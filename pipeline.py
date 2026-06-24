import requests
from bs4 import BeautifulSoup
import re
import json
import os

try:
    import pypdf
except ImportError:
    pypdf = None

class SuperYipunuPipeline:
    def __init__(self):
        self.dictionnaire_final = {} 
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def nettoyer_cle_yipunu(self, texte):
        if not texte: return ""
        # Nettoyage des marqueurs de tons scientifiques (accents circonflexes, macrons, diacritiques) fréquemment utilisés par l'INALCO
        texte = re.sub(r'[\u0300-\u036f]', '', texte) 
        # Nettoyage des parenthèses de classes nominales et des tirets lexicaux
        texte = re.sub(r'\s*\([^)]*\)', '', texte).strip()
        texte = texte.lstrip('-').rstrip('-')
        return texte.strip()

    def ajouter_traduction(self, yipunu, francais):
        """Ajoute les mots de vocabulaire stricts au dictionnaire en excluant les noms propres."""
        if not yipunu or not francais:
            return
            
        yipunu = yipunu.strip()
        francais = francais.strip()
            
        if len(yipunu) <= 1 or yipunu.lower() == francais.lower():
            return
            
        # 1. BLOQUER LES CHIFFRES ET LES STRUCTURES DE VERSETS (ex: "1:1", "14")
        if re.search(r'\d+', yipunu) or re.search(r'\d+', francais):
            return

        # 2. FILTRE STRICT DES NOMS PROPRES (Majuscule au début du mot extrait)
        if yipunu[0].isupper() or francais[0].isupper():
            return
        if yipunu.isupper() or francais.isupper():
            return

        # 3. FILTRE ANTI-PHRASES EXPLICATIVES (Garantit un dictionnaire de mots isolés)
        if len(yipunu.split()) > 3 or len(francais.split()) > 4:
            return

        # Insertion propre dans le dictionnaire de listes (gestion des synonymes)
        if yipunu not in self.dictionnaire_final:
            self.dictionnaire_final[yipunu] = []
            
        if francais not in self.dictionnaire_final[yipunu]:
            self.dictionnaire_final[yipunu].append(francais)

    def extraire_sources_web(self, url):
        print(f"🌐 Ingestion Source : {url}")
        try:
            # TÉLÉCHARGEMENT AUTOMATIQUE DES PDF ACADÉMIQUES IDENTIFIÉS
            if url.lower().endswith('.pdf') or 'file' in url.lower() or 'preview' in url.lower():
                nom_fichier_pdf = url.split('/')[-1].split('?')[0].replace('%20', '_').replace('%28', '(').replace('%29', ')')
                if not nom_fichier_pdf.endswith('.pdf'):
                    nom_fichier_pdf += ".pdf"
                
                print(f"📥 Téléchargement automatique du document : {nom_fichier_pdf}...")
                reponse = requests.get(url, headers=self.headers, timeout=30)
                if reponse.status_code == 200:
                    with open(nom_fichier_pdf, 'wb') as f:
                        f.write(reponse.content)
                    print(f"✅ Document sauvegardé localement.")
                return

            reponse = requests.get(url, headers=self.headers, timeout=15)
            if reponse.status_code != 200: return
            
            soup = BeautifulSoup(reponse.text, 'html.parser')
            
            # --- STRATÉGIE 1 : Tableaux HTML ---
            tableaux = soup.find_all('table')
            if tableaux:
                for tab in tableaux:
                    for ligne_tab in tab.find_all('tr'):
                        cellules = [c.get_text().strip() for c in ligne_tab.find_all(['td', 'th'])]
                        if len(cellules) >= 2:
                            yipunu = self.nettoyer_cle_yipunu(cellules[0])
                            francais = cellules[2] if len(cellules) == 3 else cellules[1]
                            self.ajouter_traduction(yipunu, francais)
                if self.dictionnaire_final: return

            # --- STRATÉGIE 2 : Texte brut ---
            texte_propre = soup.get_text()
            lignes = texte_propre.split('\n')
            for ligne in lignes:
                ligne = re.sub(r'\s+', ' ', ligne).strip()
                if any(t in ligne.lower() for t in ["english", "html", "javascript"]): continue
                
                match = re.match(r'^([^:-=\t]+)[:=-\t]+(.+)$', ligne)
                if match:
                    yipunu = self.nettoyer_cle_yipunu(match.group(1))
                    francais = match.group(2).strip()
                    self.ajouter_traduction(yipunu, francais)
                        
        except Exception as e:
            print(f"⚠️ Erreur sur la source {url}: {e}")

    def extraire_tous_les_pdf(self):
        if not pypdf:
            print("⚠️ pypdf non installé. Impossible de parser les livres téléchargés.")
            return

        fichiers = [f for f in os.listdir('.') if f.endswith('.pdf')]
        if not fichiers: return

        for nom_fichier in fichiers:
            print(f"📄 Extraction du lexique du PDF : {nom_fichier}")
            try:
                lecteur = pypdf.PdfReader(nom_fichier)
                for page in lecteur.pages:
                    texte_page = page.extract_text(extraction_mode="layout")
                    if not texte_page: continue
                    
                    lignes = texte_page.split('\n')
                    for ligne in lignes:
                        # Découpage par colonnes physiques (Mise en page dictionnaire)
                        parties = re.split(r'\s{2,}', ligne.strip())
                        if len(parties) >= 2:
                            yipunu = self.nettoyer_cle_yipunu(parties[0])
                            francais = parties[1].strip()
                            self.ajouter_traduction(yipunu, francais)
                            continue
                        
                        match = re.match(r'^([^:-=\t]+)[:=-\t]+(.+)$', ligne.strip())
                        if match:
                            yipunu = self.nettoyer_cle_yipunu(match.group(1))
                            francais = match.group(2).strip()
                            self.ajouter_traduction(yipunu, francais)
            except Exception as e:
                print(f"⚠️ Erreur PDF {nom_fichier}: {e}")

    def sauvegarder_dictionnaire(self):
        if not self.dictionnaire_final:
            print("⚠️ Aucun mot de dictionnaire extrait.")
            return
            
        dictionnaire_trie = dict(sorted(self.dictionnaire_final.items()))
        
        with open('dictionnaire_yipunu.json', 'w', encoding='utf-8') as f:
            json.dump(dictionnaire_trie, f, ensure_ascii=False, indent=4)
            
        print(f"🏁 Dictionnaire strict créé : {len(dictionnaire_trie)} mots de vocabulaire uniques.")

if __name__ == "__main__":
    pipeline = SuperYipunuPipeline()
    
    # 🎯 CARTOGRAPHIE DES LIENS ENRICHIE (Dépôts universitaires, CNRS & INALCO)
    urls_cibles = [
        # Source 1 : Livre de référence principal (Dictionnaire Parlons Yipunu)
        "https://theswissbay.ch/pdf/Books/Linguistics/Mega%20linguistics%20pack/African/Niger-Congo/Bantu/Punu%3B%20Parlons%20Yipunu%20%28ma-Kombil%29.pdf",
        
        # Source 2 : Thèse de doctorat du CNRS (HAL) sur les structures et devises Punu (contient de grands lexiques de vocabulaire)
        "https://theses.hal.science/tel-01368245v1/file/TOMBA_DIOGO_Amevi_Christine_Cerena_vavd.pdf",
        
        # Source 3 : Extrait de dictionnaire de linguistique descriptive des expressions figurées Yipunu (Éditions l'Harmattan via plateforme ouverte)
        "https://api.pageplace.de/preview/DT0400.9782140304279_A49321929/preview-9782140304279_A49321929.pdf",
        
        # Source 4 : Lexique structuré en ligne
        "https://mylittlewordland.com/course/379405/punu-langue-du-gabon",
        
        # Source 5 : Fiche linguistique Sorosoro (INALCO / CNRS)
        "https://sorosoro.org"
    ]
    
    for url in urls_cibles:
        pipeline.extraire_sources_web(url)
        
    pipeline.extraire_tous_les_pdf()
    pipeline.sauvegarder_dictionnaire()
