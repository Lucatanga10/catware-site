# LIRIS Super Bot (unified)

Un unico bot Discord in un solo file (`super_bot.py`) che unisce:

- Generale: messaggi di benvenuto, anti-spam, anti-phishing, log sicurezza
- Giveaway: comandi `/gstart` e `/gend` con pulsanti Join/Esci
- Ticket: pannello e canali ticket con chiusura rapida

## Requisiti

- Python 3.10+
- Un token bot Discord valido (attiva i Privileged Gateway Intents nel Developer Portal: Server Members Intent e Message Content Intent)

## Installazione

1. Apri un terminale nella cartella `liris-super-bot/`.
2. Installa le dipendenze:

   ```bash
   pip install -r requirements.txt
   ```

3. Imposta la variabile d'ambiente del token oppure crea un file `.env`:

   - Windows PowerShell:
     ```powershell
     setx DISCORD_TOKEN "IL_TUO_TOKEN"
     ```
   - Oppure crea `.env` nella cartella con il contenuto:
     ```env
     DISCORD_TOKEN=IL_TUO_TOKEN
     ```

## Avvio

```bash
python super_bot.py
```

Se vuoi una sincronizzazione slash immediata solo per un server, imposta `GUILD_ID` in cima a `super_bot.py` al tuo server ID. Altrimenti lascia `None` per la sync globale (richiede tempo).

## Comandi principali

- Generale
  - `/welcome_setup` — Imposta canale (e messaggio) di benvenuto
  - `/brand_welcome` — Imposta il nome brand per il benvenuto
  - `/security_setup` — Imposta canale dei log sicurezza

- Giveaway
  - `/gstart prize:<testo> duration:<60s|10m|2h|1d> winners:<n> channel:<#canale>`
  - `/gend [message_id]` — Se vuoto chiude l’ultimo

- Ticket
  - `/ticket_setup staff_role:@Ruolo [category:#Categoria]`
  - `/ticket_panel` — Invia il pannello con pulsanti Buy/Support

## Note

- Questo file è una versione compatta e semplificata rispetto ai tre bot originali, ma copre le funzioni essenziali. Se vuoi includere funzioni avanzate (es. transcript HTML, animazioni, slowmode anti-raid, welcome card con immagine), possiamo aggiungerle nella prossima iterazione.
- Rimuovi eventuali token incollati in chiaro dai progetti originali per sicurezza. Usa sempre `DISCORD_TOKEN`.
