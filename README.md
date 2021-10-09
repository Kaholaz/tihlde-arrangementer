# tihlde-arrangementer
Dette er et prosjekt der brukere får varsler gjennom discord når nye arrangementer åpner for påmelding på https://tihlde.org/arrangementer/

# Requirements
Programmet krever python 3.9

Python moduler som trengs for å kjøre programmet, kan lastes ned og installeres med `pip install -r requirements.txt`.

Nyeste gecko-driver kan lastes ned her: https://github.com/mozilla/geckodriver/releases

# How to run?
For å kjøre programmet må du lage en discord bot og finne bot-token-et. Dette må lagres i en .env fil der det står `BOT_TOKEN=%din bot-token%`. 
Man må også pesifisere banen til gecko-driveren.
Etter dette kan programmet kjøres ved å skrive `python Main.py`
