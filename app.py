import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'crawford-ttms-2025-secure'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crawford.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db    = SQLAlchemy(app)
bcrypt = Bcrypt(app)


# ══════════════════════════════════════════════════════════
#  MODELS
# ══════════════════════════════════════════════════════════

class Department(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False, unique=True)
    faculty     = db.Column(db.String(120), default='')
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    users       = db.relationship('User',      backref='dept_obj',  lazy=True, foreign_keys='User.department_id')
    timetables  = db.relationship('Timetable', backref='dept_obj',  lazy=True, foreign_keys='Timetable.department_id')

    def to_dict(self):
        return dict(id=self.id, name=self.name, faculty=self.faculty,
                    is_active=self.is_active,
                    student_count=len([u for u in self.users if u.role=='student']),
                    tt_count=len(self.timetables),
                    created_at=self.created_at.strftime('%d %b %Y'))


class User(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    full_name      = db.Column(db.String(120), nullable=False)
    email          = db.Column(db.String(120), unique=True, nullable=False)
    password_hash  = db.Column(db.String(256), nullable=False)
    role           = db.Column(db.String(10),  default='student')   # admin|student
    department_id  = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    level          = db.Column(db.String(10),  default='')
    is_active      = db.Column(db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    created_by     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    timetables     = db.relationship('Timetable', backref='owner',   lazy=True, foreign_keys='Timetable.owner_id')

    def dept_name(self):
        d = Department.query.get(self.department_id)
        return d.name if d else '—'

    def to_dict(self):
        creator = User.query.get(self.created_by) if self.created_by else None
        return dict(
            id=self.id, full_name=self.full_name, email=self.email,
            role=self.role,
            department_id=self.department_id,
            department=self.dept_name(),
            level=self.level,
            is_active=self.is_active,
            created_by_name=creator.full_name if creator else 'System',
            created_at=self.created_at.strftime('%d %b %Y'),
        )


class Category(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80),  nullable=False, unique=True)
    description = db.Column(db.String(200), default='')
    color       = db.Column(db.String(20),  default='#3B82F6')
    icon        = db.Column(db.String(50),  default='fa-calendar')
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    timetables  = db.relationship('Timetable', backref='category', lazy=True)

    def to_dict(self):
        return dict(id=self.id, name=self.name, description=self.description,
                    color=self.color, icon=self.icon, is_active=self.is_active,
                    count=len(self.timetables),
                    created_at=self.created_at.strftime('%d %b %Y'))


class Timetable(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    title         = db.Column(db.String(200), nullable=False)
    course_code   = db.Column(db.String(30),  nullable=False)
    course_title  = db.Column(db.String(200), default='')
    category_id   = db.Column(db.Integer, db.ForeignKey('category.id'),    nullable=False)
    owner_id      = db.Column(db.Integer, db.ForeignKey('user.id'),         nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'),   nullable=True)
    level         = db.Column(db.String(10),  default='')
    semester      = db.Column(db.String(20),  default='First')
    session_year  = db.Column(db.String(20),  default='2024/2025')
    venue         = db.Column(db.String(150), default='')
    lecturer      = db.Column(db.String(120), default='')
    status        = db.Column(db.String(20),  default='pending')
    admin_note    = db.Column(db.Text, default='')
    reviewed_by   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at   = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User',     foreign_keys=[reviewed_by])
    slots    = db.relationship('Slot',     backref='timetable', lazy=True, cascade='all, delete-orphan')

    def dept_name(self):
        d = Department.query.get(self.department_id)
        return d.name if d else '—'

    def to_dict(self):
        cat = Category.query.get(self.category_id)
        owner = User.query.get(self.owner_id)
        return dict(
            id=self.id, title=self.title, course_code=self.course_code,
            course_title=self.course_title,
            department=self.dept_name(), department_id=self.department_id,
            level=self.level, semester=self.semester, session_year=self.session_year,
            venue=self.venue, lecturer=self.lecturer, status=self.status,
            admin_note=self.admin_note or '',
            category=cat.to_dict() if cat else {},
            owner_name=owner.full_name if owner else '',
            owner_dept=owner.dept_name() if owner else '',
            reviewer_name=self.reviewer.full_name if self.reviewer else '',
            reviewed_at=self.reviewed_at.strftime('%d %b %Y %H:%M') if self.reviewed_at else '',
            created_at=self.created_at.strftime('%d %b %Y %H:%M'),
            slots=[s.to_dict() for s in self.slots],
        )


class Slot(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=False)
    day          = db.Column(db.String(15), nullable=False)
    start_time   = db.Column(db.String(10), nullable=False)
    end_time     = db.Column(db.String(10), nullable=False)
    room         = db.Column(db.String(80), default='')
    note         = db.Column(db.String(200), default='')

    def to_dict(self):
        return dict(id=self.id, day=self.day, start_time=self.start_time,
                    end_time=self.end_time, room=self.room, note=self.note)


class Notification(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    ntype      = db.Column(db.String(20), default='info')
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return dict(id=self.id, message=self.message, ntype=self.ntype,
                    is_read=self.is_read,
                    created_at=self.created_at.strftime('%d %b %Y %H:%M'))


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def cur():
    uid = session.get('uid')
    return User.query.get(uid) if uid else None

def push(user_id, msg, ntype='info'):
    db.session.add(Notification(user_id=user_id, message=msg, ntype=ntype))

def auth_req(f):
    @wraps(f)
    def d(*a, **kw):
        if not session.get('uid'):
            return jsonify(error='Login required'), 401
        return f(*a, **kw)
    return d

def admin_req(f):
    @wraps(f)
    def d(*a, **kw):
        u = cur()
        if not u or u.role != 'admin':
            return jsonify(error='Admin access required'), 403
        return f(*a, **kw)
    return d


# ══════════════════════════════════════════════════════════
#  SEED
# ══════════════════════════════════════════════════════════

def seed():
    if User.query.count():
        return

    # Departments
    depts = [
        Department(name='Computer Science',         faculty='Science & Technology'),
        Department(name='Electrical Engineering',   faculty='Engineering'),
        Department(name='Business Administration',  faculty='Management Sciences'),
        Department(name='Mass Communication',       faculty='Arts & Social Sciences'),
        Department(name='Biochemistry',             faculty='Natural Sciences'),
        Department(name='Law',                      faculty='Law'),
    ]
    for dep in depts:
        db.session.add(dep)
    db.session.flush()

    # Admin
    adm = User(
        full_name='Dr. Admin Crawford',
        email='admin@crawford.edu.ng',
        password_hash=bcrypt.generate_password_hash('admin123').decode(),
        role='admin', level='N/A',
    )
    db.session.add(adm)
    db.session.flush()

    # Students (created by admin)
    stu1 = User(
        full_name='Samuel Okafor',
        email='samuel@crawford.edu.ng',
        password_hash=bcrypt.generate_password_hash('student123').decode(),
        role='student', department_id=depts[0].id, level='300',
        created_by=adm.id,
    )
    stu2 = User(
        full_name='Chidinma Eze',
        email='chidinma@crawford.edu.ng',
        password_hash=bcrypt.generate_password_hash('student123').decode(),
        role='student', department_id=depts[1].id, level='200',
        created_by=adm.id,
    )
    stu3 = User(
        full_name='Emeka Nwosu',
        email='emeka@crawford.edu.ng',
        password_hash=bcrypt.generate_password_hash('student123').decode(),
        role='student', department_id=depts[0].id, level='400',
        created_by=adm.id,
    )
    db.session.add_all([stu1, stu2, stu3])
    db.session.flush()

    # Categories
    cats = [
        Category(name='Lecture',       description='Regular lecture sessions',       color='#2563EB', icon='fa-chalkboard-user'),
        Category(name='Lab/Practical', description='Laboratory & practical classes', color='#059669', icon='fa-flask'),
        Category(name='Tutorial',      description='Tutorial & revision sessions',   color='#D97706', icon='fa-pencil'),
        Category(name='Seminar',       description='Seminars & guest lectures',      color='#7C3AED', icon='fa-microphone-lines'),
        Category(name='Examination',   description='Tests, CATs & examinations',     color='#DC2626', icon='fa-file-pen'),
        Category(name='Workshop',      description='Skill-building workshops',       color='#DB2777', icon='fa-screwdriver-wrench'),
    ]
    for c in cats:
        db.session.add(c)
    db.session.flush()

    # Sample timetables
    tt1 = Timetable(
        title='Introduction to Programming', course_code='CSC 201',
        course_title='Introduction to Programming', category_id=cats[0].id,
        owner_id=stu1.id, department_id=depts[0].id, level='200',
        semester='First', session_year='2024/2025',
        venue='Lecture Hall A', lecturer='Dr. Emmanuel Adeyemi',
        status='approved', reviewed_by=adm.id, reviewed_at=datetime.utcnow(),
    )
    db.session.add(tt1); db.session.flush()
    for day, st, en in [('Monday','8:00','10:00'),('Wednesday','10:00','12:00'),('Friday','14:00','16:00')]:
        db.session.add(Slot(timetable_id=tt1.id, day=day, start_time=st, end_time=en, room='LH-A'))

    tt2 = Timetable(
        title='Data Structures & Algorithms', course_code='CSC 301',
        course_title='Data Structures and Algorithms', category_id=cats[0].id,
        owner_id=stu1.id, department_id=depts[0].id, level='300',
        semester='First', session_year='2024/2025',
        venue='Science Block B', lecturer='Prof. Ngozi Eze', status='pending',
    )
    db.session.add(tt2); db.session.flush()
    for day, st, en in [('Tuesday','8:00','10:00'),('Thursday','12:00','14:00')]:
        db.session.add(Slot(timetable_id=tt2.id, day=day, start_time=st, end_time=en, room='SB-B'))

    tt3 = Timetable(
        title='Circuit Analysis Lab', course_code='ENG 201',
        category_id=cats[1].id, owner_id=stu2.id,
        department_id=depts[1].id, level='200',
        semester='First', session_year='2024/2025',
        venue='Engineering Lab 1', lecturer='Dr. Akin Peters',
        status='rejected',
        admin_note='Please correct the venue and re-submit.',
        reviewed_by=adm.id, reviewed_at=datetime.utcnow(),
    )
    db.session.add(tt3); db.session.flush()
    db.session.add(Slot(timetable_id=tt3.id, day='Wednesday', start_time='14:00', end_time='17:00', room='ENG-L1'))

    tt4 = Timetable(
        title='Object Oriented Programming', course_code='CSC 401',
        category_id=cats[0].id, owner_id=stu3.id,
        department_id=depts[0].id, level='400',
        semester='First', session_year='2024/2025',
        venue='Lecture Hall C', lecturer='Prof. James Okeke', status='pending',
    )
    db.session.add(tt4); db.session.flush()
    db.session.add(Slot(timetable_id=tt4.id, day='Monday', start_time='10:00', end_time='12:00', room='LH-C'))

    # Notifications
    push(adm.id,  'Samuel Okafor submitted "Data Structures & Algorithms" awaiting review.', 'info')
    push(adm.id,  'Emeka Nwosu submitted "Object Oriented Programming" awaiting review.', 'info')
    push(stu1.id, 'Welcome to Crawford TTMS! Submit your timetables for approval.', 'info')
    push(stu1.id, 'Your timetable "Introduction to Programming" has been APPROVED! ✅', 'success')
    push(stu2.id, 'Welcome to Crawford TTMS!', 'info')
    push(stu2.id, 'Your timetable "Circuit Analysis Lab" was REJECTED. Note: Please correct the venue and re-submit.', 'error')
    push(stu3.id, 'Welcome to Crawford TTMS! Your account was created by the administrator.', 'info')

    db.session.commit()
    print('✅ Seed complete.')


# ══════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    d = request.get_json() or {}
    u = User.query.filter_by(email=(d.get('email') or '').lower().strip()).first()
    if not u or not bcrypt.check_password_hash(u.password_hash, d.get('password', '')):
        return jsonify(error='Invalid email or password'), 401
    if not u.is_active:
        return jsonify(error='Account suspended. Contact the administrator.'), 403
    session['uid'] = u.id
    return jsonify(success=True, user=u.to_dict(), role=u.role)

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify(success=True)

@app.route('/api/auth/me')
def api_me():
    u = cur()
    return jsonify(user=u.to_dict() if u else None)


# ══════════════════════════════════════════════════════════
#  DEPARTMENTS  (admin manages)
# ══════════════════════════════════════════════════════════

@app.route('/api/departments')
def get_depts():
    depts = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    return jsonify(departments=[d.to_dict() for d in depts])

@app.route('/api/departments/all')
@admin_req
def get_all_depts():
    depts = Department.query.order_by(Department.name).all()
    return jsonify(departments=[d.to_dict() for d in depts])

@app.route('/api/departments', methods=['POST'])
@admin_req
def create_dept():
    d = request.get_json() or {}
    name = (d.get('name') or '').strip()
    if not name:
        return jsonify(error='Department name is required'), 400
    if Department.query.filter_by(name=name).first():
        return jsonify(error='Department already exists'), 409
    dept = Department(name=name, faculty=(d.get('faculty') or '').strip())
    db.session.add(dept)
    db.session.commit()
    return jsonify(success=True, department=dept.to_dict()), 201

@app.route('/api/departments/<int:did>', methods=['PUT'])
@admin_req
def update_dept(did):
    dept = Department.query.get_or_404(did)
    d = request.get_json() or {}
    if 'name'      in d: dept.name      = d['name'].strip()
    if 'faculty'   in d: dept.faculty   = d['faculty'].strip()
    if 'is_active' in d: dept.is_active = d['is_active']
    db.session.commit()
    return jsonify(success=True, department=dept.to_dict())

@app.route('/api/departments/<int:did>', methods=['DELETE'])
@admin_req
def delete_dept(did):
    dept = Department.query.get_or_404(did)
    if dept.users or dept.timetables:
        dept.is_active = False
        db.session.commit()
        return jsonify(success=True, message='Department deactivated (has linked records)')
    db.session.delete(dept)
    db.session.commit()
    return jsonify(success=True, message='Department deleted')


# ══════════════════════════════════════════════════════════
#  USERS  (admin creates / manages students)
# ══════════════════════════════════════════════════════════

@app.route('/api/users')
@admin_req
def get_users():
    role   = request.args.get('role', '')
    search = request.args.get('q', '').strip()
    dept   = request.args.get('dept', type=int)
    q = User.query
    if role:   q = q.filter_by(role=role)
    if dept:   q = q.filter_by(department_id=dept)
    if search: q = q.filter(db.or_(
        User.full_name.ilike(f'%{search}%'),
        User.email.ilike(f'%{search}%'),
    ))
    return jsonify(users=[u.to_dict() for u in q.order_by(User.created_at.desc()).all()])

@app.route('/api/users', methods=['POST'])
@admin_req
def create_user():
    """Admin creates student accounts."""
    admin_user = cur()
    d = request.get_json() or {}
    fn    = (d.get('full_name') or '').strip()
    email = (d.get('email') or '').lower().strip()
    pw    = d.get('password', '')
    dept_id = d.get('department_id')
    level   = (d.get('level') or '').strip()

    if not fn:    return jsonify(error='Full name is required'), 400
    if not email: return jsonify(error='Email is required'), 400
    if len(pw) < 6: return jsonify(error='Password must be at least 6 characters'), 400
    if not dept_id: return jsonify(error='Please select a department'), 400
    if not level:   return jsonify(error='Please select a level'), 400

    if User.query.filter_by(email=email).first():
        return jsonify(error='Email already registered'), 409

    dept = Department.query.get(dept_id)
    if not dept or not dept.is_active:
        return jsonify(error='Selected department is not available'), 400

    u = User(
        full_name=fn, email=email,
        password_hash=bcrypt.generate_password_hash(pw).decode(),
        role=d.get('role', 'student'),
        department_id=int(dept_id), level=level,
        created_by=admin_user.id,
    )
    db.session.add(u)
    db.session.flush()
    push(u.id, f'Welcome to Crawford TTMS, {fn}! Your account was created by the administrator.', 'info')
    db.session.commit()
    return jsonify(success=True, user=u.to_dict()), 201

@app.route('/api/users/<int:uid>', methods=['PUT'])
@admin_req
def update_user(uid):
    u = User.query.get_or_404(uid)
    d = request.get_json() or {}
    if 'full_name'     in d: u.full_name      = d['full_name'].strip()
    if 'email'         in d: u.email          = d['email'].lower().strip()
    if 'level'         in d: u.level          = d['level']
    if 'department_id' in d: u.department_id  = d['department_id']
    if 'is_active'     in d: u.is_active      = d['is_active']
    if 'role'          in d: u.role           = d['role']
    if d.get('password') and len(d['password']) >= 6:
        u.password_hash = bcrypt.generate_password_hash(d['password']).decode()
    db.session.commit()
    return jsonify(success=True, user=u.to_dict())

@app.route('/api/users/<int:uid>/toggle', methods=['POST'])
@admin_req
def toggle_user(uid):
    u = User.query.get_or_404(uid)
    if u.id == session.get('uid'):
        return jsonify(error='Cannot suspend yourself'), 400
    u.is_active = not u.is_active
    db.session.commit()
    return jsonify(success=True, is_active=u.is_active)

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@admin_req
def delete_user(uid):
    u = User.query.get_or_404(uid)
    if u.id == session.get('uid'):
        return jsonify(error='Cannot delete yourself'), 400
    if u.timetables:
        u.is_active = False
        db.session.commit()
        return jsonify(success=True, message='User deactivated (has timetables)')
    db.session.delete(u)
    db.session.commit()
    return jsonify(success=True)


# ══════════════════════════════════════════════════════════
#  CATEGORIES
# ══════════════════════════════════════════════════════════

@app.route('/api/categories')
def get_cats():
    cats = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    return jsonify(categories=[c.to_dict() for c in cats])

@app.route('/api/categories/all')
@admin_req
def get_all_cats():
    cats = Category.query.order_by(Category.created_at.desc()).all()
    return jsonify(categories=[c.to_dict() for c in cats])

@app.route('/api/categories', methods=['POST'])
@admin_req
def create_cat():
    d = request.get_json() or {}
    name = (d.get('name') or '').strip()
    if not name: return jsonify(error='Name is required'), 400
    if Category.query.filter_by(name=name).first():
        return jsonify(error='Category already exists'), 409
    c = Category(name=name, description=(d.get('description') or '').strip(),
                 color=d.get('color', '#2563EB'), icon=d.get('icon', 'fa-calendar'))
    db.session.add(c); db.session.commit()
    return jsonify(success=True, category=c.to_dict()), 201

@app.route('/api/categories/<int:cid>', methods=['PUT'])
@admin_req
def update_cat(cid):
    c = Category.query.get_or_404(cid)
    d = request.get_json() or {}
    for f in ['name', 'description', 'color', 'icon', 'is_active']:
        if f in d: setattr(c, f, d[f])
    db.session.commit()
    return jsonify(success=True, category=c.to_dict())

@app.route('/api/categories/<int:cid>', methods=['DELETE'])
@admin_req
def delete_cat(cid):
    c = Category.query.get_or_404(cid)
    if c.timetables:
        c.is_active = False; db.session.commit()
        return jsonify(success=True, message='Category deactivated')
    db.session.delete(c); db.session.commit()
    return jsonify(success=True)


# ══════════════════════════════════════════════════════════
#  TIMETABLES
# ══════════════════════════════════════════════════════════

@app.route('/api/timetables')
@auth_req
def get_tts():
    u      = cur()
    status = request.args.get('status', '')
    cat_id = request.args.get('cat',    type=int)
    dept_id= request.args.get('dept',   type=int)
    level  = request.args.get('level',  '')
    search = request.args.get('q', '').strip()
    page   = request.args.get('page',   1, type=int)
    per    = 12

    q = Timetable.query
    if u.role != 'admin':
        q = q.filter_by(owner_id=u.id)
    if status:   q = q.filter_by(status=status)
    if cat_id:   q = q.filter_by(category_id=cat_id)
    if dept_id:  q = q.filter_by(department_id=dept_id)
    if level:    q = q.filter_by(level=level)
    if search:
        q = q.filter(db.or_(
            Timetable.course_code.ilike(f'%{search}%'),
            Timetable.title.ilike(f'%{search}%'),
            Timetable.lecturer.ilike(f'%{search}%'),
        ))

    total = q.count()
    items = q.order_by(Timetable.created_at.desc()).offset((page-1)*per).limit(per).all()
    return jsonify(timetables=[t.to_dict() for t in items],
                   total=total, pages=max(1,(total+per-1)//per), page=page)

@app.route('/api/timetables/<int:tid>')
@auth_req
def get_tt(tid):
    u  = cur()
    tt = Timetable.query.get_or_404(tid)
    if u.role != 'admin' and tt.owner_id != u.id:
        return jsonify(error='Access denied'), 403
    return jsonify(timetable=tt.to_dict())

@app.route('/api/timetables', methods=['POST'])
@auth_req
def create_tt():
    u = cur()
    d = request.get_json() or {}
    if not d.get('course_code') or not d.get('title'):
        return jsonify(error='Course code and title are required'), 400
    if not d.get('category_id'):
        return jsonify(error='Please select a category'), 400
    if not d.get('slots'):
        return jsonify(error='Add at least one time slot'), 400
    cat = Category.query.get(d['category_id'])
    if not cat or not cat.is_active:
        return jsonify(error='Category not available'), 400

    dept_id = d.get('department_id') or u.department_id
    tt = Timetable(
        title=d['title'].strip(), course_code=d['course_code'].strip().upper(),
        course_title=(d.get('course_title') or '').strip(),
        category_id=int(d['category_id']), owner_id=u.id,
        department_id=dept_id,
        level=(d.get('level') or u.level or '').strip(),
        semester=d.get('semester', 'First'),
        session_year=d.get('session_year', '2024/2025'),
        venue=(d.get('venue') or '').strip(),
        lecturer=(d.get('lecturer') or '').strip(),
        status='pending',
    )
    db.session.add(tt); db.session.flush()
    for s in d['slots']:
        if s.get('day') and s.get('start_time') and s.get('end_time'):
            db.session.add(Slot(timetable_id=tt.id, day=s['day'],
                start_time=s['start_time'], end_time=s['end_time'],
                room=(s.get('room') or '').strip(), note=(s.get('note') or '').strip()))

    for adm in User.query.filter_by(role='admin').all():
        push(adm.id, f'New timetable "{tt.title}" ({tt.course_code}) from {u.full_name} awaits review.', 'info')
    push(u.id, f'Timetable "{tt.title}" submitted and is pending admin approval.', 'info')
    db.session.commit()
    return jsonify(success=True, timetable=tt.to_dict()), 201

@app.route('/api/timetables/<int:tid>', methods=['PUT'])
@auth_req
def update_tt(tid):
    u  = cur()
    tt = Timetable.query.get_or_404(tid)
    if u.role != 'admin' and tt.owner_id != u.id:
        return jsonify(error='Access denied'), 403
    if u.role == 'student' and tt.status == 'approved':
        return jsonify(error='Cannot edit an approved timetable'), 400
    d = request.get_json() or {}
    for f in ['title','course_code','course_title','venue','lecturer','level','semester','session_year']:
        if f in d: setattr(tt, f, d[f].strip() if isinstance(d[f], str) else d[f])
    if 'category_id'   in d: tt.category_id   = int(d['category_id'])
    if 'department_id' in d: tt.department_id  = d['department_id']
    if 'slots' in d:
        Slot.query.filter_by(timetable_id=tt.id).delete()
        for s in d['slots']:
            if s.get('day') and s.get('start_time') and s.get('end_time'):
                db.session.add(Slot(timetable_id=tt.id, day=s['day'],
                    start_time=s['start_time'], end_time=s['end_time'],
                    room=(s.get('room') or '').strip()))
    if u.role == 'student' and tt.status == 'rejected':
        tt.status = 'pending'
        for adm in User.query.filter_by(role='admin').all():
            push(adm.id, f'Re-submitted timetable "{tt.title}" from {u.full_name} awaits review.', 'info')
    db.session.commit()
    return jsonify(success=True, timetable=tt.to_dict())

@app.route('/api/timetables/<int:tid>', methods=['DELETE'])
@auth_req
def delete_tt(tid):
    u  = cur()
    tt = Timetable.query.get_or_404(tid)
    if u.role != 'admin' and tt.owner_id != u.id:
        return jsonify(error='Access denied'), 403
    if u.role == 'student' and tt.status == 'approved':
        return jsonify(error='Cannot delete an approved timetable'), 400
    db.session.delete(tt); db.session.commit()
    return jsonify(success=True)

@app.route('/api/timetables/<int:tid>/review', methods=['POST'])
@admin_req
def review_tt(tid):
    u  = cur()
    tt = Timetable.query.get_or_404(tid)
    d  = request.get_json() or {}
    action = d.get('action')
    if action not in ('approve', 'reject'):
        return jsonify(error='Invalid action'), 400
    tt.status      = 'approved' if action == 'approve' else 'rejected'
    tt.admin_note  = (d.get('note') or '').strip()
    tt.reviewed_by = u.id
    tt.reviewed_at = datetime.utcnow()
    note_part = f' Note: {tt.admin_note}' if tt.admin_note else ''
    emoji     = '✅' if action == 'approve' else '❌'
    push(tt.owner_id,
         f'{emoji} Your timetable "{tt.title}" has been {"APPROVED" if action=="approve" else "REJECTED"}.{note_part}',
         'success' if action == 'approve' else 'error')
    db.session.commit()
    return jsonify(success=True, timetable=tt.to_dict())


# ══════════════════════════════════════════════════════════
#  STATS / CHARTS / SCHEDULE
# ══════════════════════════════════════════════════════════

@app.route('/api/stats')
@auth_req
def stats():
    u = cur()
    if u.role == 'admin':
        total    = Timetable.query.count()
        pending  = Timetable.query.filter_by(status='pending').count()
        approved = Timetable.query.filter_by(status='approved').count()
        rejected = Timetable.query.filter_by(status='rejected').count()
        students = User.query.filter_by(role='student').count()
        depts    = Department.query.filter_by(is_active=True).count()
        cats     = Category.query.filter_by(is_active=True).count()
        return jsonify(total=total, pending=pending, approved=approved,
                       rejected=rejected, students=students,
                       departments=depts, categories=cats)
    else:
        base = Timetable.query.filter_by(owner_id=u.id)
        return jsonify(
            total=base.count(),
            pending=base.filter_by(status='pending').count(),
            approved=base.filter_by(status='approved').count(),
            rejected=base.filter_by(status='rejected').count(),
        )

@app.route('/api/chart')
@admin_req
def chart():
    cats = Category.query.filter_by(is_active=True).all()
    return jsonify(data=[dict(
        name=c.name, color=c.color,
        approved=Timetable.query.filter_by(category_id=c.id, status='approved').count(),
        pending=Timetable.query.filter_by(category_id=c.id, status='pending').count(),
        rejected=Timetable.query.filter_by(category_id=c.id, status='rejected').count(),
    ) for c in cats])

@app.route('/api/schedule')
def schedule():
    dept_id  = request.args.get('dept',    type=int)
    level    = request.args.get('level',   '').strip()
    cat_id   = request.args.get('cat',     type=int)
    session  = request.args.get('session', '').strip()
    search   = request.args.get('q',       '').strip()
    q = Timetable.query.filter_by(status='approved')
    if dept_id: q = q.filter_by(department_id=dept_id)
    if level:   q = q.filter_by(level=level)
    if cat_id:  q = q.filter_by(category_id=cat_id)
    if session: q = q.filter_by(session_year=session)
    if search:
        q = q.filter(db.or_(
            Timetable.course_code.ilike(f"%{search}%"),
            Timetable.title.ilike(f"%{search}%"),
            Timetable.lecturer.ilike(f"%{search}%"),
            Timetable.venue.ilike(f"%{search}%"),
        ))
    items = q.order_by(Timetable.department_id, Timetable.course_code).all()
    return jsonify(timetables=[t.to_dict() for t in items], total=len(items))


@app.route('/api/sessions')
def get_sessions():
    rows = db.session.query(Timetable.session_year)\
               .filter_by(status='approved')\
               .distinct()\
               .order_by(Timetable.session_year.desc())\
               .all()
    sessions = [r[0] for r in rows if r[0]]
    return jsonify(sessions=sessions)


# ══════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════

@app.route('/api/notifs')
@auth_req
def get_notifs():
    u  = cur()
    ns = Notification.query.filter_by(user_id=u.id)\
           .order_by(Notification.created_at.desc()).limit(40).all()
    unread = Notification.query.filter_by(user_id=u.id, is_read=False).count()
    return jsonify(notifs=[n.to_dict() for n in ns], unread=unread)

@app.route('/api/notifs/read', methods=['POST'])
@auth_req
def read_notifs():
    u = cur()
    Notification.query.filter_by(user_id=u.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify(success=True)


# ══════════════════════════════════════════════════════════
#  PAGES
# ══════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('home.html', user=cur())

@app.route('/login')
def login_page():
    return redirect(url_for('dash_page')) if cur() else render_template('login.html')

@app.route('/view-timetable')
def view_timetable_page():
    return render_template('view_timetable.html', user=cur())

@app.route('/dashboard')
def dash_page():
    u = cur()
    if not u: return redirect(url_for('login_page'))
    return render_template('dashboard.html', user=u)

@app.route('/logout')
def do_logout():
    session.clear()
    return redirect(url_for('index'))


# ══════════════════════════════════════════════════════════
#  BOOTSTRAP
# ══════════════════════════════════════════════════════════

with app.app_context():
    db.create_all()
    seed()

if __name__ == '__main__':
    print('\n' + '═'*56)
    print('   Crawford TTMS — Timetable Management System')
    print('═'*56)
    print('   URL  : http://localhost:5000')
    print('   Admin: admin@crawford.edu.ng   / admin123')
    print('   Stu1 : samuel@crawford.edu.ng  / student123')
    print('   Stu2 : chidinma@crawford.edu.ng/ student123')
    print('═'*56 + '\n')
    app.run(debug=True, port=5000)
