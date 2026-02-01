# 🏟️ MatchDay Hub

**MatchDay Hub** is a fully automated, serverless sports aggregator designed specifically for **Android TV** and web browsers. It fetches live sports events, filters them intelligently, and presents them in a clean, dark/light-optimized interface.

![Status](https://img.shields.io/badge/status-live-brightgreen) ![Update](https://img.shields.io/badge/updates-every_15_mins-blue)

## ✨ Features

* **📺 TV-First Design:** Large UI elements, readable fonts, and easy remote control navigation.
* **🧠 Persistent Memory:** The system "remembers" active games even if the source API glitches briefly.
* **⏳ Smart Filtering:** Automatically removes events 4 hours after start time or when explicitly marked as finished.
* **🌍 Multi-Sport Support:** Auto-detection for Football, NBA, NFL, F1, MotoGP, and more.
* **🚀 Serverless:** Runs entirely on GitHub Actions and GitHub Pages. No hosting costs.

## 🛠️ How it Works

1.  **Trigger:** A GitHub Action cron job runs every 15 minutes.
2.  **Fetch:** The Python script queries the live sports API.
3.  **Process:** It merges new data with the persistent JSON memory file.
4.  **Generate:** It builds a static `index.html` file with the latest schedule.
5.  **Deploy:** The site is instantly published via GitHub Pages.

## ⚠️ Disclaimer

This project is for educational purposes only. It acts as a data visualizer for public API endpoints. No content is hosted on this repository.

---
*Maintained by Oriol*
