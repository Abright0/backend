# Backend

A Django-based backend API for managing a multi-vendor delivery platform.

## Project Structure

```
backend/
├── accounts/          # User management and authentication
├── stores/           # Store/vendor management  
├── orders/           # Order processing and tracking
└── deliveries/       # Delivery assignments and logistics
```

## Features

- **User Management**: User registration, authentication, and profile management
- **Store Management**: Multi-vendor store setup and management
- **Order Processing**: Order creation, tracking, and status management
- **Delivery System**: Order assignment and delivery coordination

## Architecture

Built with Django REST Framework, this backend provides a scalable API for:
- User accounts and authentication
- Store registration and management
- Order lifecycle management
- Delivery tracking and assignment

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Start the server: `python manage.py runserver`

## API Endpoints

The API provides endpoints for all core functionality across accounts, stores, orders, and deliveries modules.
