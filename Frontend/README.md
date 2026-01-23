# 💻 REFLECT – The Website (Frontend)

This is the "face" of the project. It's the website where you record your audio and see your journals.

---

## 📑 Index
1. [Simple Overview](#-simple-overview)
2. [One-Click Setup](#-one-click-setup)
3. [Manual Setup](#-manual-setup)
4. [How to Update](#-how-to-update)
5. [For Developers](#-for-developers)

---

## 💡 Simple Overview
This part of the project handles the **look and feel**. It doesn't do any "thinking" (that's the Backend's job). 

**What can you do here?**
- **Dashboard:** See your recent entries and quick actions.
- **Recording Hub:** Record live audio or upload a file.
- **Journal Viewer:** Read your transcripts, edit them, and see AI insights.
- **Insights:** View a page dedicated to your data patterns and metrics.

---

## 🚀 One-Click Setup
If you haven't done so yet, go back to the [Main Folder](../) and run:
- **Windows:** `setup.bat`
- **Mac:** `setup.command`

This will automatically install all the design tools and set up the website for you.

---

## 🛠️ Manual Setup
1. Make sure you have **Node.js** installed.
2. Open your terminal in this `Frontend` folder.
3. Run `npm install` (this downloads the design tools).
4. Run `npm run dev` (this starts the website).
5. Open `http://localhost:3000` in your browser.

---

## 🔄 How to Update
To get the latest visual changes and dashboard features, run this command in the main project folder:
```bash
git pull
```

---

## 🏗️ For Developers
This project is built with **Next.js 15** and **Tailwind CSS**.

### Folder Map:
- **`app/`**: The core application pages including Dashboard, Analytics, Editor, and Recordings.
- **`components/`**: Modular building blocks organized by feature (Recording, Transcript, Analytics, etc.).
- **`components/ui/`**: Basic design primitives like text boxes and buttons (shadcn/ui).
- **`lib/`**: Utility functions and API integration logic for backend communication.
- **`context/`**: Global state providers, such as the `ServerStatusContext` for monitoring engine health.
- **`public/`**: Static assets like icons, logos, and images used throughout the application.

### Styling:
We use a **Zinc/Neutral** color palette for a clean, professional look. Most of the styling is done directly in the HTML files using Tailwind classes.

### Important Note:
The website checks if the **Backend** is online. If you see "Engine Offline" in the top right, make sure you have the Backend terminal running!
