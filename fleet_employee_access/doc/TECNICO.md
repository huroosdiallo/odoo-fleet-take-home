# fleet_employee_access: note tecniche

Estende le app standard `fleet` e `hr_fleet` di Odoo 19 e aggiunge solo quello che manca al compito.

## Già nello standard

- `fleet.vehicle` con targa, marca e modello, viste, menu e storico delle assegnazioni.
- `hr_fleet`: collegamento al dipendente (`driver_employee_id`, sincronizzato con `driver_id`) e pulsante «Cars History» sul dipendente.
- Gruppi Officer (in italiano «Manager: gestisce tutti i veicoli») e Administrator.

## Aggiunto

- **Gruppo `group_fleet_own_vehicles`** («Utente Base: solo i propri veicoli»), sotto Officer, che lo implica. Ha ACL di lettura, scrittura e creazione sui veicoli (niente eliminazione) e regole `driver_employee_id.user_id = utente` su veicoli, contachilometri, contratti, interventi e storico assegnazioni. Officer ha regole `[(1, '=', 1)]` che mantengono il comportamento standard.
- **Blocco della riassegnazione:** le regole di scrittura si valutano sul record prima della modifica, quindi `create` e `write` controllano dipendente, conducente e futuro conducente. `default_get` propone il proprio dipendente.
- **`driver_employee_id` modificabile** (in `hr_fleet` è in sola lettura), con onchange sul conducente.
- **Marche e modelli:** l'Officer li può creare e modificare, anche al volo dal form. Per l'Utente Base il campo Modello ha `no_create`.
- **Colori multipli:** modello `fleet.vehicle.color` e campo `color_ids` (`many2many_tags`). Il campo testo standard `color` è nascosto nel form.
- **Viste:** dipendente visibile in form e lista, filtro e menu «Le mie auto», ricerca e raggruppamento per dipendente, menu Configurazione › Modelli › Colori.
- **Traduzione italiana** in `i18n/it.po`.
- **Dati demo:** utenti `fleet_base` (Utente Base, 2 auto) e `fleet_manager` (Manager), con password uguale al login.

## Test

`tests/test_fleet_employee_access.py` (18 test): gerarchia dei gruppi, visibilità per ruolo, creazione, blocco della riassegnazione, eliminazione, dati collegati, anagrafiche, colori, viste e menu.

Con i dati demo il test standard `fleet:TestFleet.test_change_future_driver` fallisce anche senza questo modulo.
