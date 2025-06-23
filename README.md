# WhisperCore Backend

A secure and private AI confidant and assistant backend built with Flask.

## Features

- Secure user authentication with JWT
- Private memory vault for journaling
- Weekly and monthly AI-generated reflections
- Mood tagging system
- RESTful API endpoints
- Docker support
- Modular architecture

## Prerequisites

- Python 3.11+
- Docker (optional)
- PostgreSQL (for production)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd whispercore-backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
DATABASE_URL=sqlite:///dev.db  # For development
```

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

## Running the Application

### Development
```bash
flask run
```

### Production with Docker
```bash
docker build -t whispercore-backend .
docker run -p 5000:5000 whispercore-backend
```

## API Endpoints

### Authentication
- POST `/api/auth/register` - Register a new user
- POST `/api/auth/login` - Login and get JWT token
- GET `/api/auth/profile` - Get current user info

### Memories
- POST `/api/memories` - Create a new memory
- GET `/api/memories` - Get all memories
- GET `/api/memories/<id>` - Get specific memory
- PUT `/api/memories/<id>` - Update memory
- DELETE `/api/memories/<id>` - Delete memory

### Reflections
- POST `/api/reflections` - Create a new reflection
- GET `/api/reflections` - Get all reflections
- GET `/api/reflections/<id>` - Get specific reflection
- DELETE `/api/reflections/<id>` - Delete reflection

## Security

- All data is encrypted at rest
- JWT-based authentication
- CORS protection
- Input validation
- SQL injection protection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 