import os
import re
import math
from collections import Counter
import pdfplumber
import docx

def load_stopwords(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return set(word.strip().lower() for word in f.read().splitlines() if word.strip())
    return set()

class INIdrisStemmer:
    def __init__(self):
        self.dictionary = set()
        self.load_dictionary("kata-dasar.txt")
        
        self.suffixes_list = [
            "an","at","i", "iah", "ilah", "in","is","isme","kan","lah","nya","wan","wi"
        ]

        self.prefixes_list = [
            "be","bel","ber","di","dwi","ke","me","mem","men","meng","meny","mono","pe","pel","pem","pen","peng","peny","per","pra","pro","se","sub","ter"
        ]

    def load_dictionary(self, path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                words = f.read().splitlines()
                self.dictionary = set(word.strip().lower() for word in words if word.strip())
        else:
            print(f"File {path} tidak ditemukan. Dictionary kosong.")

    def is_vowel(self, char):
        return char.lower() in 'aiueo'

    def remove_suffix(self, word):
        for suffix in self.suffixes_list:
            if word.endswith(suffix):
                return word[:-len(suffix)]
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

    def remove_prefix(self, word):
        for prefix in self.prefixes_list:
            if word.startswith(prefix):
                return word[len(prefix):]
        return word

    def stem(self, word):
        current_word = word
        
        if current_word in self.dictionary:
            return current_word

        for prefix in self.prefixes_list:
            if current_word.startswith(prefix):
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
            return self.stem(processed_suffix)

        return word

def preprocessing(text):
    stemmer = INIdrisStemmer()
    stopwords = load_stopwords("stopwords.txt")
    
    text = text.replace("-", " ")
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", text.lower())
    tokens = clean.split()
    
    filtered_tokens = [t for t in tokens if t not in stopwords]
    
    stemmed_tokens = [stemmer.stem(token) for token in filtered_tokens]
    return stemmed_tokens

folder_path = "JournalMedis"

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

files = os.listdir(folder_path)

print("\nNama path:", folder_path)

doc_database = []
global_doc_freq = Counter()
total_docs = 0
index = 1

for file in files:
    full_path = os.path.join(folder_path, file)

    if not os.path.isfile(full_path):
        continue

    text = ""
    if file.endswith(".txt"):
        with open(full_path, "r", encoding="utf-8") as f:
            text = f.read()

    elif file.endswith(".pdf"):
        with pdfplumber.open(full_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    text += txt + " "

    elif file.endswith(".docx"):
        doc = docx.Document(full_path)
        for para in doc.paragraphs:
            text += para.text + " "

    else:
        continue
    
    total_docs += 1
    
    tokens = preprocessing(text)
    
    freq = Counter(tokens)
    # print(f"\n    ({index}). {file}")
    # print("        Mengandung kata:")
    # for word, count in freq.items():
    #     print(f"                {word} = {count}")
    
    unique_tokens = set(tokens)
    
    doc_database.append({
        "filename": file,
        "terms": unique_tokens
    })
    
    for token in unique_tokens:
        global_doc_freq[token] += 1
        
    index += 1

print(f"\nTotal Dokumen (|D|) ditemukan: {total_docs}")

st_values = {}

print("\n" + "="*50)
print(f"{'Term (t)':<20} | {'|Dt|':<10} | {'st':<10}")
print("="*50)

sorted_terms = sorted(global_doc_freq.keys())

for term in sorted_terms:
    Dt = global_doc_freq[term]
    
    st = (Dt + 0.5) / (total_docs + 1.0)
    st_values[term] = st
    
    print(f"{term:<20} | {Dt:<10} | {st:.4f}")

print("="*50)

while True:
    query_input = input("\nMasukkan Query (ketik 'exit' untuk keluar): ")
    if query_input.lower() == 'exit':
        break
        
    query_tokens = set(preprocessing(query_input))
    print(f"Query Tokens: {query_tokens}")
    
    results = []
    
    print(f"\n{'FILENAME':<30} | {'CALCULATION LOG DETAILS'}")
    print("-" * 80)

    for doc in doc_database:
        score = 0
        doc_terms = doc["terms"]
        calc_details = []
        
        for term in query_tokens:
            if term in doc_terms and term in st_values:
                st = st_values[term]
                
                weight = math.log10((1 - st) / st)
                score += weight
                calc_details.append(f"log((1-{st:.2f})/{st:.2f})")
        
        if score > 0:
            calc_str = " + ".join(calc_details)
            print(f"{doc['filename']:<30} | {calc_str} = {score:.4f}")
            results.append({
                "filename": doc["filename"],
                "score": score
            })
            
    results.sort(key=lambda x: x["score"], reverse=True)
    
    print("\n" + "="*40)
    print("HASIL PERANKINGAN DOKUMEN")
    print("="*40)
    
    if not results:
        print("Tidak ada dokumen yang relevan.")
    else:
        print(f"{'RANK':<5} {'SCORE':<10} {'FILENAME'}")
        print("-" * 40)
        for i, res in enumerate(results, 1):
            print(f"{i:<5} {res['score']:<10.4f} {res['filename']}")