package com.laroska.golesempates;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebSettings;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

public class MainActivity extends Activity {
    private static final String GOLES = "https://analisis-goles-diario.laroska.chatgpt.site/";
    private static final String EMPATES = BuildConfig.EMPATES_SERVER_URL.isEmpty() ? "https://empates-hoy-diario.laroska.chatgpt.site/" : BuildConfig.EMPATES_SERVER_URL;
    private final int navy = Color.rgb(12, 26, 49);
    private final int green = Color.rgb(20, 130, 89);
    private final int blue = Color.rgb(39, 99, 190);
    private WebView web;
    private TextView status;
    private String current = GOLES;
    private boolean historyMode = false;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(navy);
        setContentView(root);

        TextView title = new TextView(this);
        title.setText("⚽  GOLES HOY");
        title.setTextColor(Color.WHITE);
        title.setTextSize(20);
        title.setTypeface(null, Typeface.BOLD);
        title.setGravity(Gravity.CENTER);
        title.setPadding(dp(8), dp(16), dp(8), dp(12));
        root.addView(title, new LinearLayout.LayoutParams(-1, -2));

        LinearLayout row2 = row(root);
        addButton(row2, "📊 HISTORIAL", Color.rgb(70, 79, 102), this::history);
        addButton(row2, "↻ ACTUALIZAR", Color.rgb(170, 105, 28), this::refresh);

        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setTextSize(11);
        status.setPadding(dp(12), dp(6), dp(12), dp(9));
        root.addView(status, new LinearLayout.LayoutParams(-1, -2));

        web = new WebView(this);
        web.setBackgroundColor(Color.WHITE);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setCacheMode(WebSettings.LOAD_NO_CACHE);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                status.setText("Consultando fecha publicada · " + paraguayTime());
                if (url.startsWith("https://")) {
                    // La fecha visible del sitio es distinta de la fecha de apertura de la APK.
                    // Nunca presentar la fecha del teléfono como fecha del pronóstico.
                    view.evaluateJavascript("(function(){var t=document.body.innerText||'';var m=t.match(/(?:APOSTALA\\s*[·•\\-]\\s*|(?:an[aá]lisis|pron[oó]sticos|empates|goles)\\s+(?:del|de|para|hoy)\\s*[:·-]?\\s*)(\\d{1,2})\\s*(?:de\\s*)?(SEP(?:TIEMBRE)?|OCT(?:UBRE)?|AGO(?:STO)?|NOV(?:IEMBRE)?|DIC(?:IEMBRE)?|ENE(?:RO)?|FEB(?:RERO)?|MAR(?:ZO)?|ABR(?:IL)?|MAY(?:O)?|JUN(?:IO)?|JUL(?:IO)?)/i);if(!m)m=t.match(/\\b(\\d{1,2})[\\/.-](\\d{1,2})[\\/.-](?:20)?\\d{2}\\b/);return m?m[1]+'|'+m[2]:''})()", result -> {
                        String reported = result == null ? "" : result.replace("\"", "");
                        if (reported.contains("|")) {
                            String[] parts = reported.split("\\|", 2);
                            SimpleDateFormat dayFmt = new SimpleDateFormat("d", Locale.US);
                            SimpleDateFormat monthFmt = new SimpleDateFormat("M", Locale.US);
                            TimeZone py = TimeZone.getTimeZone("America/Asuncion");
                            dayFmt.setTimeZone(py);
                            monthFmt.setTimeZone(py);
                            String month = parts[1].toUpperCase(Locale.US);
                            int foundMonth = -1;
                            String[] months = {"ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"};
                            for (int i = 0; i < months.length; i++) if (month.startsWith(months[i])) foundMonth = i + 1;
                            if (foundMonth < 0) try { foundMonth = Integer.parseInt(month); } catch (Exception ignored) {}
                            boolean old = !dayFmt.format(new Date()).equals(parts[0]) || foundMonth != Integer.parseInt(monthFmt.format(new Date()));
                            if (old) {
                                status.setText("⚠ " + (current.equals(EMPATES) ? "EMPATES" : "GOLES") + " SIN ACTUALIZAR: " + reported.replace('|', ' ') + " · Hoy " + paraguayTime() + ". El servidor debe publicar los nuevos partidos.");
                            } else {
                                status.setText("Fecha visible coincide con hoy · " + paraguayTime() + " · Verificá los partidos publicados");
                            }
                        } else {
                            status.setText("Hoy " + paraguayTime() + " · No se pudo confirmar la fecha de los pronósticos del sitio");
                        }
                    });
                }
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) status.setText("No se pudo cargar. Comprobá tu conexión y el sitio web.");
            }
        });
        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
        open(GOLES);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private LinearLayout row(LinearLayout root) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(dp(5), 0, dp(5), 0);
        root.addView(row, new LinearLayout.LayoutParams(-1, dp(53)));
        return row;
    }

    private void addButton(LinearLayout row, String label, int color, Runnable action) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextColor(Color.WHITE);
        button.setTextSize(12);
        button.setTypeface(null, Typeface.BOLD);
        button.setAllCaps(false);
        button.setPadding(dp(2), 0, dp(2), 0);
        GradientDrawable background = new GradientDrawable();
        background.setColor(color);
        background.setCornerRadius(dp(10));
        button.setBackground(background);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(43), 1f);
        params.setMargins(dp(4), dp(4), dp(4), dp(4));
        row.addView(button, params);
        button.setOnClickListener(v -> action.run());
    }

    private String paraguayTime() {
        SimpleDateFormat fmt = new SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault());
        fmt.setTimeZone(TimeZone.getTimeZone("America/Asuncion"));
        return fmt.format(new Date()) + " (PY)";
    }

    private void open(String url) {
        current = url;
        historyMode = false;
        status.setText(url.equals(EMPATES) && BuildConfig.EMPATES_SERVER_URL.isEmpty() ? "⚠ EMPATES: servidor nuevo no configurado; sitio anterior puede mostrar fecha vieja" : "Cargando página...");
        web.loadUrl(url + (url.contains("?") ? "&" : "?") + "v=" + System.currentTimeMillis());
    }

    private void history() {
        historyMode = true;
        current = "";
        status.setText("Historial de goles: consultá los resultados publicados.");
        web.loadDataWithBaseURL(null,
            "<!doctype html><html lang='es'><meta name='viewport' content='width=device-width,initial-scale=1'>" +
            "<body style='font:17px sans-serif;padding:20px;background:#f5f7fb;color:#12233e'>" +
            "<h2>📊 HISTORIAL</h2><p>Consultá los resultados reales en cada plataforma. " +
            "Los pronósticos acertados y fallados dependen de los datos publicados en sus sitios.</p>" +
            "<p>Usá el botón ACTUALIZAR para consultar los datos del sitio. " +
            "La APK no inventa resultados ni modifica pronósticos anteriores.</p></body></html>",
            "text/html", "UTF-8", null);
    }

    private void refresh() {
        web.clearCache(true);
        if (historyMode) {
            history();
            Toast.makeText(this, "Volvé al sitio para ver datos recientes", Toast.LENGTH_LONG).show();
        } else {
            status.setText("Consultando datos recientes del sitio...");
            web.loadUrl(current + (current.contains("?") ? "&" : "?") + "v=" + System.currentTimeMillis());
        }
    }

    @Override public void onBackPressed() {
        if (!current.isEmpty() && web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
