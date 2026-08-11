# PlacePrep

## Overview

PlacePrep is a Django-based educational assessment platform that enables educational institutions to manage cohorts, question banks, assessments, and student attempts. The system supports multiple question types including single choice, multiple choice, numerical, short answer, and coding questions with automatic evaluation for objective questions and manual grading for coding questions.

## Features

- Cohort management with faculty and student coordinators
- Comprehensive question bank with five question types
- Assessment creation and scheduling with time windows
- Student attempt management with auto-submission
- Automatic evaluation for objective questions
- Manual grading interface for coding questions
- Role-based access control (Admin, Faculty, Student Coordinator, Student)

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/accounts/login/` | User login |
| POST | `/accounts/logout/` | User logout |

### Cohorts
| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/cohorts/` | List cohorts | Authenticated users |
| GET | `/api/cohorts/{id}/` | Cohort details | Authenticated users |
| POST | `/cohorts/create/` | Create cohort | Admin only |
| POST | `/cohorts/{id}/edit/` | Update cohort | Admin only |

### Questions
| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/questions/` | List approved questions | Content Author |
| GET | `/questions/{id}/` | Question details | Content Author |
| POST | `/questions/create/` | Create question | Content Author |
| POST | `/questions/{id}/edit/` | Update question | Content Author |

### Assessments
| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/assessments/` | List assessments | Authenticated users |
| GET | `/assessments/{id}/` | Assessment details | Authenticated users |
| POST | `/assessments/create/` | Create assessment | Content Author |
| POST | `/assessments/{id}/edit/` | Update assessment | Content Author |
| GET | `/assessments/{id}/start/` | Start attempt | Cohort members |

### Attempts
| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/api/attempts/` | List attempts | Authenticated users |
| GET | `/attempts/{id}/` | Attempt details | Owner/Faculty/Admin |
| POST | `/attempts/{id}/submit/` | Submit attempt | Owner |
| POST | `/attempts/{id}/grade/` | Grade attempt | Faculty/Admin |
| POST | `/attempts/{attempt_id}/questions/{aq_id}/save/` | Save answer | Owner |

## Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager
- PostgreSQL (recommended) or SQLite

### Steps

1. Fork the repository
```bash
git clone https://github.com/yourusername/placeprep.git
cd placeprep
```

2. Create virtual environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment variables
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
```

5. Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create superuser
```bash
python manage.py createsuperuser
```

7. Run development server
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Testing APIs with Postman

### 1. Authentication
First, login to get session cookies:
```
POST http://localhost:8000/accounts/login/
Data: username=admin&password=admin123
```

### 2. List Cohorts
```
GET http://localhost:8000/api/cohorts/
Authorization: Basic Auth (username:password)
```

### 3. Create a Question (Single Choice)
```
POST http://localhost:8000/questions/create/
Content-Type: application/json
Authorization: Basic Auth

{
  "text": "What is 2+2?",
  "question_type": "SINGLE_CHOICE",
  "marks": 2,
  "negative_marks": 0.5,
  "choices": [
    {"text": "3", "is_correct": false},
    {"text": "4", "is_correct": true},
    {"text": "5", "is_correct": false}
  ]
}
```

### 4. Create an Assessment
```
POST http://localhost:8000/assessments/create/
Content-Type: application/json
Authorization: Basic Auth

{
  "title": "Midterm Exam",
  "description": "Covers all topics",
  "cohort": 1,
  "start_datetime": "2026-07-27T10:00:00Z",
  "end_datetime": "2026-07-27T12:00:00Z",
  "max_attempts": 1,
  "duration_minutes": 120,
  "status": "DRAFT",
  "assessment_questions": [
    {"question": 1, "marks": 2, "order": 1}
  ]
}
```

### 5. Start Attempt
```
GET http://localhost:8000/assessments/1/start/
Authorization: Basic Auth
```

### 6. Save Answer (Single Choice)
```
POST http://localhost:8000/attempts/1/questions/1/save/
Content-Type: application/json
Authorization: Basic Auth

{
  "choice": 2
}
```

### 7. Save Answer (Coding)
```
POST http://localhost:8000/attempts/1/questions/2/save/
Content-Type: application/json
Authorization: Basic Auth

{
  "code_answer": "function add(a,b) { return a+b; }"
}
```

### 8. Submit Attempt
```
POST http://localhost:8000/attempts/1/submit/
Authorization: Basic Auth
```

### 9. View Attempt Results
```
GET http://localhost:8000/attempts/1/
Authorization: Basic Auth
```

### 10. Grade Attempt (Faculty/Admin only)
```
POST http://localhost:8000/attempts/1/grade/
Content-Type: application/json
Authorization: Basic Auth

{
  "marks_1": 8,
  "feedback_1": "Good solution, but consider edge cases"
}
```

## Sample Request Bodies

### Multiple Choice Question
```json
{
  "text": "Which are programming languages?",
  "question_type": "MULTIPLE_CHOICE",
  "marks": 3,
  "negative_marks": 0.5,
  "choices": [
    {"text": "Python", "is_correct": true},
    {"text": "HTML", "is_correct": false},
    {"text": "Java", "is_correct": true}
  ]
}
```

### Numerical Question
```json
{
  "text": "What is 10 * 5?",
  "question_type": "NUMERICAL",
  "marks": 1,
  "negative_marks": 0.25,
  "correct_numeric_answer": 50
}
```

### Short Answer Question
```json
{
  "text": "What is the capital of France?",
  "question_type": "SHORT_ANSWER",
  "marks": 1,
  "negative_marks": 0,
  "correct_text_answer": "Paris"
}
```

### Coding Question
```json
{
  "text": "Write a function to add two numbers",
  "question_type": "CODING",
  "marks": 10,
  "negative_marks": 0,
  "coding_test_cases": [
    {"input": "1,2", "expected": "3"},
    {"input": "5,7", "expected": "12"}
  ]
}
```

### Multiple Choice Answer Save
```json
{
  "choices": [1, 3, 5]
}
```

### Numerical Answer Save
```json
{
  "numeric_answer": 42
}
```

### Short Answer Save
```json
{
  "text_answer": "My answer here"
}
```

## User Roles

- **Admin**: Full access, can manage cohorts, approve content
- **Faculty Coordinator**: Create questions, manage assessments, grade attempts
- **Student Coordinator**: Create questions and assessments (no publishing/grading)
- **Student**: Attempt assessments, view results

## Database Models

- **Cohort**: Groups students with faculty and student coordinators
- **Question**: Assessment questions with type-specific fields
- **Assessment**: Contains questions, timing, and visibility settings
- **Attempt**: Student attempt with status tracking
- **Answer**: Student responses to questions

## Error Responses

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid data |
| 403 | Permission Denied |
| 404 | Not Found |
| 500 | Internal Server Error |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

