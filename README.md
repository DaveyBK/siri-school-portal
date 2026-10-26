# School Inventory Management System (Pear v2)

A comprehensive desktop application for managing school inventory, library books, student records, attendance, and class schedules. Built with Python and Tkinter, designed specifically for educational institutions.

## Features

### Core Functionality
- **Student Management**: Add, edit, search, and track student records
- **Inventory Tracking**: Manage library books and school equipment
- **Attendance System**: Daily attendance tracking with schedule integration
- **QR Code Integration**: Generate and scan QR codes for quick checkout/check-in
- **Book Checkout System**: Track book assignments and returns
- **Class Schedule Management**: Import and manage class schedules
- **Secure Authentication**: Password-protected access with bcrypt encryption
- **Data Import/Export**: CSV import functionality for bulk data management
- **Backup System**: Automatic database backups with restore capability

### User Experience
- **Interactive Tutorial System**: 8 built-in step-by-step tutorials for training new users
- **Modern UI**: Clean, intuitive tabbed interface
- **Search Functionality**: Fast search across students, books, and inventory
- **Data Validation**: Built-in validation to ensure data integrity
- **Audit Trail**: Track changes and events in the system
- **Archive Management**: Archive and restore historical data

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Display**: Minimum 1024x768 resolution recommended

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/school-inventory-system.git
cd school-inventory-system
```

### 2. Set Up Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `Pillow >= 10.0.0` - Image processing for student photos
- `qrcode[pil] >= 7.4.2` - QR code generation
- `bcrypt >= 4.0.0` - Secure password hashing
- `tkinter` - GUI framework (bundled with Python)

**Note**: On Linux, if tkinter is not installed:
```bash
sudo apt-get install python3-tk
```

### 4. Configure Credentials

Create your credentials file:

```bash
cp data/credentials.example.json data/credentials.json
```

Edit `data/credentials.json` and set your admin password. To generate a hashed password, run:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'your_password', bcrypt.gensalt()).decode())"
```

Replace the `password` field in `credentials.json` with the generated hash.

### 5. Initialize Database

The database will be created automatically on first run. You can also initialize it manually:

```bash
python -c "from inventory.db import init_db; init_db()"
```

## Usage

### Running the Application

```bash
python app.py
```

### First Time Setup

1. **Login**: Use the credentials configured in `data/credentials.json`
2. **Import Data**: Navigate to the appropriate tab and use import features
3. **Configure Schedule**: Load your class schedule via the Schedule tab
4. **Add Students**: Manually add students or import from CSV
5. **Add Inventory**: Add books and equipment to track

### Learning the System

Click the purple **"📚 Tutorials"** button at the bottom of the screen to access interactive tutorials:

1. Add a New Student
2. Check Out a Book
3. Take Daily Attendance
4. Search for Students or Books
5. Return a Book
6. Add a New Book/Item
7. Generate QR Codes
8. Load Class Schedule

See [QUICK_START.md](QUICK_START.md) for detailed tutorial instructions.

## Project Structure

```
school-inventory-system/
├── app.py                    # Main application entry point
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
│
├── inventory/               # Core business logic
│   ├── db.py               # Database initialization and utilities
│   ├── db_schema.py        # Database schema definitions
│   ├── models.py           # Data models
│   ├── validation.py       # Input validation
│   ├── qr_utils.py         # QR code generation utilities
│   ├── password_utils.py   # Password hashing utilities
│   ├── archival.py         # Data archival functionality
│   ├── audit.py            # Audit trail logging
│   └── events.py           # Event management
│
├── ui/                      # User interface components
│   ├── main_window.py      # Main application window
│   ├── login.py            # Login window
│   ├── schedule_tab.py     # Schedule management tab
│   ├── tutorial_system_simple.py  # Tutorial system
│   └── components/         # Reusable UI components
│
├── scripts/                 # Utility scripts
│   ├── csv_importer_gui.py # CSV import interface
│   ├── schedule_import.py  # Schedule import utilities
│   ├── cleanup_*.py        # Data cleanup scripts
│   └── migrate_*.py        # Database migration scripts
│
├── data/                    # Application data (NOT in git)
│   ├── credentials.json    # User credentials (SENSITIVE)
│   ├── inventory.db        # Main database (SENSITIVE)
│   └── backups/            # Automatic backups (SENSITIVE)
│
├── tests/                   # Test files
│
└── docs/                    # Additional documentation
    ├── CSV_IMPORTER_INTEGRATION.md
    ├── IMPLEMENTATION_SUMMARY.md
    ├── TUTORIAL_SYSTEM_README.md
    └── TUTORIAL_VISUAL_GUIDE.md
```

## Configuration

### Credentials (`data/credentials.json`)

```json
{
  "username": "admin",
  "password": "$2b$12$...",
  "login_required": true
}
```

- `username`: Admin username
- `password`: Bcrypt-hashed password
- `login_required`: Set to `false` to bypass login (not recommended)

### Database

The SQLite database (`data/inventory.db`) stores:
- Student records
- Inventory items
- Book checkout history
- Attendance records
- Class schedules
- Audit logs

### Backups

Automatic backups are created in `data/backups/` with timestamps. To restore a backup, replace `data/inventory.db` with a backup file.

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Building Executable

To create a standalone executable:

```bash
python -m PyInstaller "School Portal.spec"
```

The executable will be created in the `dist/` directory.

### Adding New Features

1. **Database Changes**: Update schema in `inventory/db_schema.py`
2. **Business Logic**: Add functionality in `inventory/` modules
3. **UI Components**: Create or modify files in `ui/`
4. **Scripts**: Add utility scripts to `scripts/`

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular

## Security Considerations

### Sensitive Data

This application handles sensitive information:
- Student personal data
- School inventory records
- User credentials

### Best Practices

1. **Never commit sensitive data** to version control
2. **Use strong passwords** and enable login
3. **Regular backups** - keep multiple backup copies
4. **Access control** - limit who can access the system
5. **Update dependencies** regularly for security patches

### Data Privacy

Ensure compliance with relevant data protection regulations (FERPA, GDPR, etc.) when handling student information.

## Troubleshooting

### Database Issues

**Problem**: Database locked error
**Solution**: Close all other instances of the application

**Problem**: Database corrupted
**Solution**: Restore from `data/backups/`

### Import Issues

**Problem**: CSV import fails
**Solution**: Ensure CSV format matches expected structure (see CSV_IMPORTER_INTEGRATION.md)

### UI Issues

**Problem**: Window too small or elements cut off
**Solution**: Increase screen resolution or maximize window

**Problem**: Tutorial overlay stuck
**Solution**: Press Escape or click "Skip Tutorial"

### Installation Issues

**Problem**: Tkinter not found
**Solution**: Install python3-tk package (Linux) or reinstall Python with Tk support

## Documentation

- [QUICK_START.md](QUICK_START.md) - Getting started guide
- [TUTORIAL_SYSTEM_README.md](TUTORIAL_SYSTEM_README.md) - Tutorial system documentation
- [CSV_IMPORTER_INTEGRATION.md](CSV_IMPORTER_INTEGRATION.md) - CSV import guide
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical implementation details

## Contributing

### Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Reporting Issues

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

## License

This project is proprietary software for educational institutions. Unauthorized distribution or commercial use is prohibited.

## Acknowledgments

- Built for school administrators and teachers
- Designed with non-technical users in mind
- Tutorial system inspired by modern onboarding experiences

## Support

For support, questions, or feature requests:
1. Check existing documentation
2. Try the built-in tutorials
3. Contact your system administrator
4. Open an issue on GitHub (for technical problems)

---

**Version**: 2.0
**Last Updated**: November 2025
**Maintained by**: School IT Department
