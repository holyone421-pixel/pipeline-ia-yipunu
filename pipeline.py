import requests
from bs4 import BeautifulSoup
import re
import json

class YipunuPipeline:
    def __init__(self):
        self.dictionnaire_final = {}
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def nettoyer_cle_yipunu(self, texte):
        texte = re.sub(r'\s*\([^)]*\)', '', texte).strip()
        return texte.lstrip('-').strip()

    def extraire_source_standard(self, url):
        print(f"🔄 Ingestion automatique de la source : {url}")
        try:
            reponse = requests.get(url, headers=self.headers, timeout=15)
            if reponse.status_code != 200: return
            
            lignes = reponse.text.split('\n')
            for ligne in lignes:
                ligne = re.sub(r'\s+', ' ', ligne).strip()
                mots = ligne.split(' ')
                
                if len(mots) >= 3 and not any(t in ligne.lower() for t in ["yipunu", "english", "français"]):
                    yipunu = self.nettoyer_cle_yipunu(mots)
                    francais = " ".join(mots[2:]).strip()
                    
                    if len(yipunu) > 1 and yipunu.lower() != francais.lower():
                        self.dictionnaire_final[yipunu] = francais
        except Exception as e:
            print(f"⚠️ Erreur sur {url}: {e}")

    def sauvegarder_donnees(self):
        if not self.dictionnaire_final:
            print("⚠️ Aucun token extrait lors de cette session. Sauvegarde annulée.")
            return
            
        dictionnaire_trie = dict(sorted(self.dictionnaire_final.items()))
        
        with open('dictionnaire_yipunu.json', 'w', encoding='utf-8') as f:
            json.dump(dictionnaire_trie, f, ensure_ascii=False, indent=4)
            
        print(f"🏁 Synchronisation cloud réussie. {len(dictionnaire_trie)} tokens yipunu validés.")

if __name__ == "__main__":
    pipeline = YipunuPipeline()
    
    # Vos sources de confiance
    sources = [
        "http://free.fr",
        "http://free.fr",
        "https://blogspot.com"
    ]
    
    for source in sources:
        pipeline.extraire_source_standard(source)
        
    pipeline.sauvegarder_donnees()
