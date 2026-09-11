# Minds Agency Factuur App / PWA

Dit is een algemene factuur-app voor Minds Agency. Je kunt hem gebruiken voor Otera en voor alle andere klanten.

## Wat zit erin?

- Dashboard met betaald, openstaand, over datum en klanten
- Klanten toevoegen en beheren
- Facturen maken voor elke klant
- Meerdere factuurregels per factuur
- Automatisch 21% btw
- Automatisch vervaldatum: factuurdatum + 14 dagen
- PDF facturen downloaden in de vaste Minds Agency stijl
- Mailtekst per factuur genereren
- Statusknoppen: open, betaald, concept
- PWA app: op telefoon toevoegen aan beginscherm

## Starten op je MacBook

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open daarna:

```bash
http://127.0.0.1:5000
```

## Online zetten via GitHub + Railway

1. Maak een nieuwe GitHub repository.
2. Upload alle bestanden uit deze map.
3. Ga naar Railway.
4. Kies New Project.
5. Kies Deploy from GitHub repo.
6. Selecteer deze repo.
7. Railway gebruikt automatisch de Procfile.
8. Na deploy krijg je een link.
9. Open de link op je telefoon.
10. iPhone: delenknop > Zet op beginscherm.
11. Android: Chrome menu > Toevoegen aan startscherm.

## Belangrijk voor later

Deze eerste versie gebruikt SQLite. Dat werkt prima om te starten. Voor een zware zakelijke versie kunnen we later toevoegen:

- Login
- Medewerkers/rollen
- PostgreSQL database
- Factuur bewerken
- Automatische herinneringen
- Betaallinks
- Uploaden naar boekhouding
