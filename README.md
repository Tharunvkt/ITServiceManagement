# IT Service Request Management System

## Project Overview
The IT Service Request Management System is a Django-based web application that helps organizations manage IT support requests efficiently. It allows users to create service requests, track their status, and monitor resolution deadlines.

## Features
- User authentication and access control
- Create and manage IT service requests
- Request categories and priority levels
- Assign requests to IT staff
- Request lifecycle management
- SLA deadline tracking and breach alerts
- Resolution details and resolution-time tracking
- Comments and request history
- Dashboard with request statistics
- Reports with status and priority summaries
- Filter requests by status and priority

## Technology Stack
- **Backend:** Python, Django
- **Frontend:** HTML, CSS, Bootstrap
- **Database:** SQLite
- **Tools:** Visual Studio Code, Git, GitHub

## SLA Rules
| Priority | Resolution Target |
|---|---|
| Critical | 4 hours |
| High | 8 hours |
| Medium | 24 hours |
| Low | 48 hours |

The system identifies requests that are approaching their deadlines, have breached their SLA, or were resolved within or after the SLA deadline.

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone YOUR_GITHUB_REPOSITORY_URL
   ```

2. Navigate into the project folder:
   ```bash
   cd ITServiceManagement
   ```

3. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   ```

   Windows:
   ```bash
   venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Apply database migrations:
   ```bash
   python manage.py migrate
   ```

6. Create an administrator account if needed:
   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:
   ```bash
   python manage.py runserver
   ```

8. Open `http://127.0.0.1:8000/` in your browser.

## Testing
Run the Django system check:
```bash
python manage.py check
```

Run the application tests:
```bash
python manage.py test
```

## Future Improvements
- Email notifications for SLA breaches
- Advanced analytics and visual reports
- Automated assignment of requests
- Improved automated test coverage

## Author
Developed as an IT Service Request Management System hackathon project.
