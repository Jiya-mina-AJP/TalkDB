# TalkDB - EasifAI Text-to-SQL Explorer ⚡

TalkDB (powered by **EasifAI**) is a premium, professional Streamlit web application that lets users upload SQLite databases, SQL scripts, or CSV files and query them using plain English. 

The application translates your questions into executable SQL statements via the Google Gemini API, runs them against your uploaded database, displays the interactive results, and provides a natural language summary explaining the findings.

---

## ✨ Features

* **Natural Language to SQL**: Simply ask questions like *"What is the average GPA of students in 12th class?"* and get instant SQL code and results.
* **Smart Schema Explorer**: Automatically parses your uploaded SQLite databases (`.db`/`.sqlite`), SQL schemas, or multiple CSV files to visualize table structures, column types, and sample data.
* **Premium Dark Theme**: Sleek black and violet modern UI design with responsive controls and micro-animations.
* **Multi-User Isolation**: Automatically generates session-specific staging databases to prevent data collisions when multiple users query the app concurrently.
* **Export Options**: Download any generated table query results as a `.csv` file.
* **History Logs**: Keeps track of your query session so you can easily reference previous questions, SQL commands, and results.

---

## 🛠️ Tech Stack

* **Frontend & Server**: Python, Streamlit
* **Database**: SQLite3, Pandas
* **AI Model**: Google Gemini API (`gemini-2.5-flash`)
* **Styling**: Custom CSS (Inter & JetBrains Mono typography)

---

## 🚀 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Jiya-mina-AJP/TalkDB.git
   cd TalkDB
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your API Key:**
   * Create a `.env` file in the root directory:
     ```env
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

5. **Generate the Sample Database (Optional):**
   ```bash
   python sql.py
   ```

6. **Run the application:**
   ```bash
   streamlit run app.py
   ```
   Open your browser to `http://localhost:8501` to view and use the application!
