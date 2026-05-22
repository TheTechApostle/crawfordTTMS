from app import app

if __name__ == '__main__':
    print('\n' + '='*58)
    print('  Crawford TTMS — Timetable Management System')
    print('='*58)
    print('  Home        : http://localhost:5000')
    print('  Timetables  : http://localhost:5000/view-timetable')
    print('  Login       : http://localhost:5000/login')
    print('  Dashboard   : http://localhost:5000/dashboard')
    print('  ---')
    print('  Admin   : admin@crawford.edu.ng  / admin123')
    print('  Student : samuel@crawford.edu.ng / student123')
    print('  Student : chidinma@crawford.edu.ng / student123')
    print('='*58 + '\n')
    app.run(debug=True, port=5000)
