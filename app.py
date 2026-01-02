import os
import re
import math
import logging
import sys
from collections import Counter
from flask import Flask, render_template, request, jsonify
import pdfplumber
import docx

logging.getLogger("pdfminer").setLevel(logging.ERROR)

app = Flask(__name__)

FOLDER_PATH = "JournalMedis"
if not os.path.exists(FOLDER_PATH):
    os.makedirs(FOLDER_PATH)

def load_stopwords(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return set(word.strip().lower() for word in f.read().splitlines() if word.strip())
    return set()

class INIdrisStemmer:
    def __init__(self):
        self.dictionary = set()
        self.load_dictionary("kata-dasar.txt")
        self.suffixes_list = sorted([
            "an","at","i", "iah", "ilah", "in","is","isme","kan","lah","nya","wan","wi", "tah", "ku", "mu"
        ], key=len, reverse=True)
        self.prefixes_list = sorted([
            "be","bel","ber","di","dwi","ke","me","mem","men","meng","meny","mono","pe","pel","pem","pen","peng","peny","per","pra","pro","se","sub","ter"
        ], key=len, reverse=True)

    def load_dictionary(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                words = f.read().splitlines()
                self.dictionary = set(word.strip().lower() for word in words if word.strip())

    def is_vowel(self, char):
        return char.lower() in 'aiueo'

    def remove_suffix(self, word):
        for suffix in self.suffixes_list:
            if word.endswith(suffix):
                if len(word) > len(suffix): 
                    return word[:-len(suffix)]
        return word

    def remove_prefix(self, word):
        for prefix in self.prefixes_list:
            if word.startswith(prefix):
                if len(word) > len(prefix):
                    return word[len(prefix):]
        return word

    def apply_rule2(self, word):
        if (word.startswith("men") or word.startswith("pen")) and len(word) > 3 and self.is_vowel(word[3]):
            return "t" + word[3:]
        if (word.startswith("meng") or word.startswith("peng")) and len(word) > 4 and self.is_vowel(word[4]):
            return "k" + word[4:]
        if (word.startswith("meny") or word.startswith("peny")) and len(word) > 4 and self.is_vowel(word[4]):
            return "s" + word[4:]
        if (word.startswith("mem") or word.startswith("pem")) and len(word) > 3 and self.is_vowel(word[3]):
            return "p" + word[3:]
        return word

    def stem(self, word):
        current_word = word
        if current_word in self.dictionary:
            return current_word
        for prefix in self.prefixes_list:
            if current_word.startswith(prefix):
                if len(current_word) > len(prefix):
                    candidate = current_word[len(prefix):]
                    if candidate in self.dictionary:
                        return candidate
        processed_rule2 = self.apply_rule2(current_word)
        if processed_rule2 != current_word:
            if processed_rule2 in self.dictionary:
                return processed_rule2
            prefix_rule2 = self.remove_prefix(processed_rule2)
            if prefix_rule2 in self.dictionary:
                return prefix_rule2
        processed_suffix = self.remove_suffix(current_word)
        if processed_suffix != current_word:
            if len(processed_suffix) > 1:
                return self.stem(processed_suffix)
        return word

def get_preprocessing_steps(text):
    stemmer = INIdrisStemmer()
    stopwords = load_stopwords("stopwords.txt")
    text = text.lower()
    text = re.sub(r'(?<=\d),(?=\d)', '.', text)
    text = re.sub(r'(?<!\d)\.|\.(?!\d)', ' ', text)
    text = text.replace("-", " ")
    case_folded = re.sub(r"[^a-zA-Z0-9\s\.]", " ", text)
    tokens = case_folded.split()
    
    filtered = []
    for t in tokens:
        t_clean = t.strip()
        if t_clean and t_clean not in stopwords:
            if len(t_clean) > 1 or t_clean.replace('.', '', 1).isdigit():
                filtered.append(t_clean)
    
    stemmed = []
    for t in filtered:
        if re.match(r'^\d+(\.\d+)?%?$', t):
            stemmed.append(t)
        else:
            res = stemmer.stem(t)
            if res and len(res) > 0:
                stemmed.append(res)
            else:
                stemmed.append(t)
            
    final_tokens = [t for t in stemmed if len(t) > 1 or t.replace('.', '', 1).isdigit()]
    
    return {
        'original': text,
        'case_folded': case_folded,
        'tokens': tokens,
        'filtered': filtered,
        'stemmed': final_tokens,
        'pairs': list(zip(filtered, final_tokens))
    }

def extract_text(filename):
    full_path = os.path.join(FOLDER_PATH, filename)
    text = ""
    try:
        if filename.endswith(".txt"):
            with open(full_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif filename.endswith(".pdf"):
            with pdfplumber.open(full_path) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text()
                    if txt: text += txt + " "
        elif filename.endswith(".docx"):
            doc = docx.Document(full_path)
            for para in doc.paragraphs:
                text += para.text + " "
    except Exception as e:
        print(f"\nError reading {filename}: {e}")
    return text

doc_database = []
global_doc_freq = Counter()
st_values = {}
total_docs = 0

def build_index():
    global doc_database, global_doc_freq, st_values, total_docs
    if doc_database:
        return

    doc_database = []
    global_doc_freq = Counter()
    total_docs = 0
    
    files = [f for f in os.listdir(FOLDER_PATH) if os.path.isfile(os.path.join(FOLDER_PATH, f))]
    total_files_count = len(files)
    
    print(f"\nMemulai proses indexing {total_files_count} dokumen...")
    
    for i, file in enumerate(files, 1):
        percent = (i / total_files_count) * 100
        bar_length = 30
        filled_length = int(bar_length * i // total_files_count)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\r[{bar}] {percent:.1f}% | Memproses: {file[:20]:<20}')
        sys.stdout.flush()

        text = extract_text(file)
        if not text: continue
        steps = get_preprocessing_steps(text)
        final_tokens = steps['stemmed']
        unique_tokens = set(final_tokens)
        doc_database.append({
            "filename": file,
            "terms": unique_tokens,
            "count_base": len(final_tokens),
            "freq": Counter(final_tokens)
        })
        for token in unique_tokens:
            global_doc_freq[token] += 1
        total_docs += 1
    
    print("\n\nMenghitung bobot probabilistik...")
    st_values = {}
    for term in global_doc_freq:
        Dt = global_doc_freq[term]
        st = (Dt + 0.5) / (total_docs + 1.0)
        st_values[term] = st
    print("Indexing selesai! Server siap dijalankan.\n")

build_index()

@app.route('/api/terms')
def api_terms():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').lower()
    order = request.args.get('order', 'asc')
    per_page = 20
    
    all_terms = list(st_values.items())
    
    if search:
        all_terms = [t for t in all_terms if search in t[0]]
        
    all_terms.sort(key=lambda x: x[0], reverse=(order == 'desc'))
    
    total_terms = len(all_terms)
    start = (page - 1) * per_page
    end = start + per_page
    sliced_terms = all_terms[start:end]
    
    data = []
    for term, st in sliced_terms:
        data.append({
            'term': term,
            'dt': global_doc_freq[term],
            'st': f"{st:.4f}"
        })
        
    return jsonify({
        'data': data,
        'current_page': page,
        'total_pages': math.ceil(total_terms / per_page),
        'total_terms': total_terms
    })

@app.route('/', methods=['GET', 'POST'])
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    results = []
    query = ""
    query_tokens = []
    
    if request.method == 'POST':
        query = request.form.get('query', '')
        steps = get_preprocessing_steps(query)
        query_tokens = set(steps['stemmed'])
        
        for doc in doc_database:
            score = 0
            doc_terms = doc["terms"]
            calc_details = []
            for term in query_tokens:
                if term in doc_terms and term in st_values:
                    st = st_values[term]
                    weight = math.log10((1 - st) / st)
                    score += weight
                    calc_details.append(f"log((1-{st:.4f})/{st:.4f}) <span class='text-indigo-600 font-bold bg-indigo-50 px-1 rounded'>[{term}]</span>")
            if score > 0:
                results.append({
                    "filename": doc["filename"],
                    "score": score,
                    "calc": " + ".join(calc_details)
                })
        results.sort(key=lambda x: x["score"], reverse=True)

    total_files = len(doc_database)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_files = doc_database[start_idx:end_idx]
    total_pages = math.ceil(total_files / per_page)
    
    return render_template('index.html', 
                           files=paginated_files, 
                           total_docs=total_docs,
                           results=results,
                           query=query,
                           query_tokens=query_tokens,
                           current_page=page,
                           total_pages=total_pages)

@app.route('/detail/<filename>')
def detail(filename):
    text = extract_text(filename)
    steps = get_preprocessing_steps(text)
    word_counts = Counter(steps['stemmed'])
    return render_template('detail.html', 
                           filename=filename, 
                           steps=steps, 
                           word_counts=word_counts)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)