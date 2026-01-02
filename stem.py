import os
import re
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
            "isme", "ilah", "iah", "kan", "nya", "wan", 
            "an", "at", "in", "is", "wi", "lah", "i",
            "kah", "tah", "pun", "ku", "mu"
        ]

        self.prefixes_list = [
            "meng", "meny", "peng", "peny", "mono",
            "mem", "men", "pem", "pen", "bel", "ber", "dwi", "pel", "per", "pra", "pro", "sub", "ter",
            "be", "di", "ke", "me", "pe", "se"
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

def tokenize(text):
    stemmer = INIdrisStemmer()
    stopwords = load_stopwords("stopwords.txt")
    
    text = text.replace("-", " ")
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", text.lower())
    tokens = clean.split()
    
    filtered_tokens = [t for t in tokens if t not in stopwords]
    
    stemmed_tokens = [stemmer.stem(token) for token in filtered_tokens]
    return Counter(stemmed_tokens)

folder_path = "documents"

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

files = os.listdir(folder_path)

print("\nNama path:", folder_path)

index = 1

for file in files:
    full_path = os.path.join(folder_path, file)

    if not os.path.isfile(full_path):
        continue

    if file.endswith(".txt"):
        with open(full_path, "r", encoding="utf-8") as f:
            text = f.read()

    elif file.endswith(".pdf"):
        text = ""
        with pdfplumber.open(full_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    text += txt + " "

    elif file.endswith(".docx"):
        doc = docx.Document(full_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + " "

    else:
        continue

    freq = tokenize(text)

    print(f"\n    ({index}). {file}")
    print("        Mengandung kata:")

    for word, count in freq.items():
        print(f"                {word} = {count}")

    index += 1