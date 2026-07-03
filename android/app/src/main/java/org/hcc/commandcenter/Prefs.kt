package org.hcc.commandcenter

import android.content.Context

class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("hcc", Context.MODE_PRIVATE)

    fun serverUrl(): String =
        sp.getString(KEY_URL, DEFAULT_URL) ?: DEFAULT_URL

    fun saveServerUrl(url: String) {
        sp.edit().putString(KEY_URL, url.ifBlank { DEFAULT_URL }).apply()
    }

    companion object {
        private const val KEY_URL = "server_url"
        // USB adb reverse — works when phone is plugged in
        private const val DEFAULT_URL = "http://127.0.0.1:8787/today"
    }
}