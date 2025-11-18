import sqlite3
import hashlib
import json
from datetime import datetime
import os

class Database:
    def __init__(self, db_name="parentadvocate.db"):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                user_type TEXT DEFAULT 'parent',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Case details table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS case_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                children_names TEXT,
                children_ages TEXT,
                case_number TEXT,
                dcp_worker_name TEXT,
                dcp_worker_contact TEXT,
                court_date TEXT,
                separation_date TEXT,
                case_type TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT,
                category TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_analysis TEXT,
                file_data BLOB,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Violations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                violation_type TEXT NOT NULL,
                description TEXT,
                date_occurred TEXT,
                legislation_reference TEXT,
                evidence TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Compliance tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                category TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                completion_date TEXT,
                notes TEXT,
                evidence_file_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Appointments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                appointment_type TEXT NOT NULL,
                date_time TEXT NOT NULL,
                location TEXT,
                status TEXT DEFAULT 'scheduled',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Child updates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS child_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                child_name TEXT,
                update_type TEXT,
                update_text TEXT,
                date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Reflections/journal table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reflection_text TEXT NOT NULL,
                date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Chat history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # DCP communications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dcp_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                direction TEXT,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, email, password, full_name, user_type='parent'):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = self.hash_password(password)
            cursor.execute('''
                INSERT INTO users (email, password_hash, full_name, user_type)
                VALUES (?, ?, ?, ?)
            ''', (email, password_hash, full_name, user_type))
            conn.commit()
            user_id = cursor.lastrowid
            
            # Create default case details entry
            cursor.execute('''
                INSERT INTO case_details (user_id)
                VALUES (?)
            ''', (user_id,))
            conn.commit()
            
            conn.close()
            return True, "Account created successfully"
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Email already exists"
        except Exception as e:
            conn.close()
            return False, str(e)
    
    def verify_user(self, email, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = self.hash_password(password)
        cursor.execute('''
            SELECT id, full_name, user_type FROM users 
            WHERE email = ? AND password_hash = ?
        ''', (email, password_hash))
        
        user = cursor.fetchone()
        
        if user:
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (user[0],))
            conn.commit()
        
        conn.close()
        return user
    
    def get_user_stats(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get case details
        cursor.execute('SELECT * FROM case_details WHERE user_id = ?', (user_id,))
        case = cursor.fetchone()
        
        # Count violations
        cursor.execute('SELECT COUNT(*) FROM violations WHERE user_id = ? AND status = "open"', (user_id,))
        violations_count = cursor.fetchone()[0]
        
        # Count pending tasks
        cursor.execute('SELECT COUNT(*) FROM compliance_tasks WHERE user_id = ? AND status = "pending"', (user_id,))
        pending_tasks = cursor.fetchone()[0]
        
        # Count completed tasks
        cursor.execute('SELECT COUNT(*) FROM compliance_tasks WHERE user_id = ? AND status = "completed"', (user_id,))
        completed_tasks = cursor.fetchone()[0]
        
        # Calculate compliance percentage
        total_tasks = pending_tasks + completed_tasks
        compliance_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Count upcoming appointments
        cursor.execute('SELECT COUNT(*) FROM appointments WHERE user_id = ? AND status = "scheduled"', (user_id,))
        upcoming_appointments = cursor.fetchone()[0]
        
        # Get documents count
        cursor.execute('SELECT COUNT(*) FROM documents WHERE user_id = ?', (user_id,))
        documents_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'violations': violations_count,
            'compliance_pct': round(compliance_pct, 1),
            'pending_tasks': pending_tasks,
            'completed_tasks': completed_tasks,
            'appointments': upcoming_appointments,
            'documents': documents_count,
            'case_details': case
        }
    
    def save_chat_message(self, user_id, role, message):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (user_id, role, message)
            VALUES (?, ?, ?)
        ''', (user_id, role, message))
        conn.commit()
        conn.close()
    
    def get_chat_history(self, user_id, limit=50):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, message, timestamp FROM chat_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        messages = cursor.fetchall()
        conn.close()
        return list(reversed(messages))
    
    def add_document(self, user_id, filename, file_type, category, file_data, ai_analysis=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO documents (user_id, filename, file_type, category, file_data, ai_analysis)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, filename, file_type, category, file_data, ai_analysis))
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()
        return doc_id
    
    def get_documents(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, filename, file_type, category, upload_date, ai_analysis
            FROM documents WHERE user_id = ?
            ORDER BY upload_date DESC
        ''', (user_id,))
        docs = cursor.fetchall()
        conn.close()
        return docs
    
    def add_violation(self, user_id, violation_type, description, date_occurred, legislation_ref="", evidence=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO violations (user_id, violation_type, description, date_occurred, legislation_reference, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, violation_type, description, date_occurred, legislation_ref, evidence))
        conn.commit()
        conn.close()
    
    def get_violations(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, violation_type, description, date_occurred, legislation_reference, status, created_at
            FROM violations WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        violations = cursor.fetchall()
        conn.close()
        return violations
    
    def add_compliance_task(self, user_id, task_name, category, due_date, notes=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO compliance_tasks (user_id, task_name, category, due_date, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, task_name, category, due_date, notes))
        conn.commit()
        conn.close()
    
    def get_compliance_tasks(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, task_name, category, due_date, status, completion_date, notes
            FROM compliance_tasks WHERE user_id = ?
            ORDER BY due_date
        ''', (user_id,))
        tasks = cursor.fetchall()
        conn.close()
        return tasks
    
    def update_task_status(self, task_id, status):
        conn = self.get_connection()
        cursor = conn.cursor()
        completion_date = datetime.now().strftime("%Y-%m-%d") if status == "completed" else None
        cursor.execute('''
            UPDATE compliance_tasks 
            SET status = ?, completion_date = ?
            WHERE id = ?
        ''', (status, completion_date, task_id))
        conn.commit()
        conn.close()
    
    def add_appointment(self, user_id, appointment_type, date_time, location, notes=""):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO appointments (user_id, appointment_type, date_time, location, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, appointment_type, date_time, location, notes))
        conn.commit()
        conn.close()
    
    def get_appointments(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, appointment_type, date_time, location, status, notes
            FROM appointments WHERE user_id = ?
            ORDER BY date_time
        ''', (user_id,))
        appointments = cursor.fetchall()
        conn.close()
        return appointments
    
    def add_reflection(self, user_id, reflection_text, date):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reflections (user_id, reflection_text, date)
            VALUES (?, ?, ?)
        ''', (user_id, reflection_text, date))
        conn.commit()
        conn.close()
    
    def get_reflections(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT reflection_text, date, created_at
            FROM reflections WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        reflections = cursor.fetchall()
        conn.close()
        return reflections
    
    def update_case_details(self, user_id, **kwargs):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        if fields:
            values.append(user_id)
            query = f"UPDATE case_details SET {', '.join(fields)} WHERE user_id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
    
    def get_case_details(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM case_details WHERE user_id = ?', (user_id,))
        case = cursor.fetchone()
        conn.close()
        return case