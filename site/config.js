// Configura qui i tuoi link/ID. Questo file è caricato da tutte le pagine.
// Modifica SOLO i valori fra virgolette.

// PayPal.me username (pagamenti personali Amici/Parenti)
// Esempio: window.PAYPAL_ME = "Luca123";
window.PAYPAL_ME = "";

// Revolut username (revolut.me)
// Esempio: window.REVOLUT_USER = "luca";
window.REVOLUT_USER = "@lucatangaa010";

// PayPal Client ID (opzionale per bottone PayPal Checkout)
// Se vuoi il bottone PayPal ufficiale, inserisci qui il tuo Client ID (sandbox o live)
// Esempio: window.PAYPAL_CLIENT_ID = "AbCdEf...";
window.PAYPAL_CLIENT_ID = window.PAYPAL_CLIENT_ID || "";

// Valuta di default per Stripe / link
window.DEFAULT_CURRENCY = window.DEFAULT_CURRENCY || "EUR";

// Email del venditore per ricevere notifica d'ordine (facoltativo)
// Esempio: window.MERCHANT_EMAIL = "tuaemail@example.com";
window.MERCHANT_EMAIL = window.MERCHANT_EMAIL || "";

// Link di download/guida per ogni prodotto/variante (opzionale)
// Inserisci link a Google Drive/Dropbox o una pagina di istruzioni.
// Le chiavi devono combaciare con gli ID in shop.js (es: cat_private_day, temp_day, perm_onetime...)
window.DOWNLOAD_LINKS = Object.assign({
  cat_private_day: "",
  cat_private_week: "",
  cat_private_month: "",
  cat_private_life: "",
  temp_day: "",
  temp_week: "",
  temp_month: "",
  temp_life: "",
  perm_onetime: "",
  perm_life: "",
}, window.DOWNLOAD_LINKS || {});
