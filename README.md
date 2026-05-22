# Crawford TTMS — Timetable Management System

## Setup & Run

```bash
pip install -r requirements.txt
python run.py
```

Open: http://localhost:5000

## Login Credentials

| Role    | Email                          | Password    |
|---------|-------------------------------|-------------|
| Admin   | admin@crawford.edu.ng          | admin123    |
| Student | student@crawford.edu.ng        | student123  |
| Student | chidinma@crawford.edu.ng       | student123  |

## Features

### Admin
- Manage all timetables (view, review, approve, reject, delete)
- Manage categories (create, edit, enable/disable, delete)
- Manage users (activate, suspend, reset passwords)
- Reports & Analytics with charts
- Notifications for all student submissions

### Student
- Register and log in
- Submit timetables for admin approval
- Choose from admin-managed categories
- Edit/resubmit rejected timetables
- View approval status and admin notes
- Weekly schedule visual grid
- Notifications for approvals/rejections

## Tech Stack
- Backend: Python Flask + SQLAlchemy + SQLite
- Frontend: HTML, CSS, Tailwind CDN, Vanilla JS
- Charts: Chart.js
- Icons: Font Awesome 6
