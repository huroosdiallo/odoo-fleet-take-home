# custom_fleet_vehicle: note tecniche

Parco auto scritto da zero, senza l'app Fleet. Dipende da `base`, `mail` e `hr`.

## Modelli

- `custom.fleet.vehicle`: targa (obbligatoria, unica, normalizzata in maiuscolo senza spazi, 2-12 tra lettere, cifre e trattini), marca, modello, colori (Many2many), anno, dipendente (`hr.employee`), `user_id` (related stored dal dipendente), azienda, note. Eredita `mail.thread` e `mail.activity.mixin`. L'immagine è quella del modello.
- Anagrafiche `custom.fleet.vehicle.brand`, `.model` e `.color`, con nomi unici senza distinguere le maiuscole (i modelli sono unici per marca). Un vincolo impedisce un modello di un'altra marca.
- `hr.employee`: smart button **Auto** con il numero di auto visibili all'utente.

## Sicurezza

| Gruppo | Auto | Anagrafiche |
|---|---|---|
| Utente Base | lettura, scrittura, creazione; regola `user_id = utente` | lettura |
| Manager (implica Utente Base) | tutto; regola `[(1, '=', 1)]` | tutto |

C'è anche una regola globale multi-azienda. Le regole di scrittura si valutano sul record prima della modifica, quindi `create` e `write` controllano anche il risultato: un Utente Base non può assegnare un'auto ad altri, toglierle il dipendente o prendersi un'auto libera. Nel form i campi delle anagrafiche sono duplicati per gruppo, così solo il Manager può crearle al volo.

## Viste

Lista, kanban per dipendente, form, pivot, grafico, attività e ricerca, con i filtri «Le mie auto», «Non assegnate», «Senza colore» e «Archiviate». Menu: Le mie auto, Tutte le auto e Configurazione (solo per il Manager).

## Test

`tests/` (29 test): visibilità e permessi per gruppo, blocco della riassegnazione, targa, anagrafiche, onchange marca/modello, colori, smart button, tracking e caricamento delle viste.

## Limiti

- La targa è unica in tutto il database, non per azienda.
- Un'auto senza dipendente con utente la vede solo il Manager.
