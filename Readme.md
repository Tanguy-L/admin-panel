# Admin Team Management PLG

## Overview

This is a Flask-based web application for managing team members, authentication, and team operations. The application provides RESTful APIs for handling members, teams, and user authentication with JWT (JSON Web Token) based security.

## Features

- User Authentication
  - JWT-based login system
  - Protected routes requiring authentication
- Member Management
  - Add, update, and delete members
  - Retrieve member information
  - Support for batch member updates
- Team Management
  - Create and manage teams
  - Assign members to teams
  - Team weight balancing
- Database Connectivity
  - MySQL database integration
  - Transaction management
  - Connection pooling

## Tech Stack

- Backend: Flask
- Database: MySQL
- Authentication: Flask-JWT-Extended
- ORM/Database Connector: mysql-connector-python
- Environment Management: python-dotenv
- CORS Handling: flask-cors

## Project Structure

```
project-root/
│
├── core/                   # Core configuration and database utilities
│   ├── config.py           # Application configuration settings
│   └── database.py         # Database connection and transaction management
│
├── models/                 # Data models and DTOs
│   ├── member.py           # Member data model
│   └── team.py             # Team data model
│
├── repositories/           # Data access layer
│   ├── member.py           # Member database operations
│   ├── team.py             # Team database operations
│   └── team_member.py      # Team-member relationship management
│
├── routes/                 # API route handlers
│   ├── auth.py             # Authentication routes
│   ├── members.py          # Member-related routes
│   └── teams.py            # Team-related routes
│
├── services/               # Business logic services
│   └── team_balancer.py    # Team balancing algorithm
│
└── app.py                  # Main application entry point
```

## Prerequisites

- Python 3.8+
- MySQL Database
- pip (Python package manager)

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd <project-directory>
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment variables
Create a `.env` file with the following variables:
```
PLG_HOST=your_database_host
PLG_USERNAME=your_database_username
PLG_PASSWORD=your_database_password
PLG_DATABASE=your_database_name
PLG_PORT=your_database_port

APP_HOST=0.0.0.0
APP_PORT=8000

APP_USERNAME=your_app_username
APP_PASSWORD=your_app_password
```

## Running the Application

```bash
python app.py
```

## API Endpoints

### Authentication
- `POST /auth/login`: Authenticate and receive JWT token
- `GET /auth/protected`: Test authenticated route

### Members
- `GET /members`: Retrieve all members
- `POST /members`: Add one or multiple members
- `PUT /members/<member_id>`: Update a member
- `DELETE /members/<member_id>`: Delete a member

### Teams
- `GET /teams`: Retrieve all teams

## Security

- JWT-based authentication
- CORS configured for `http://localhost:3000`
- Secure environment variable management

## Database Transactions

The application uses context managers for database transactions, ensuring:
- Automatic commit on successful operations
- Automatic rollback on errors
- Proper connection and cursor management

## Team Balancing

The `TeamBalancer` service provides an algorithm to assign members to teams based on their weight, ensuring balanced team composition.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Your Name - your.email@example.com

Project Link: [Repository URL]
