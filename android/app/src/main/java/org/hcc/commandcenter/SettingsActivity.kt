package org.hcc.commandcenter

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class SettingsActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = Prefs(this)
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 48, 48, 48)
        }
        layout.addView(TextView(this).apply {
            text = "HCC server URL"
            textSize = 18f
        })
        val input = EditText(this).apply {
            setText(prefs.serverUrl())
            hint = "http://192.168.x.x:8787/today"
        }
        layout.addView(input)
        layout.addView(TextView(this).apply {
            text = "\nUSB (plugged in): http://127.0.0.1:8787/today\nWi‑Fi: http://YOUR_PC_IP:8787/today"
            textSize = 14f
        })
        layout.addView(Button(this).apply {
            text = "Save"
            setOnClickListener {
                prefs.saveServerUrl(input.text.toString().trim())
                finish()
            }
        })
        setContentView(layout)
    }
}