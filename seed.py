from models import db, User, Room


def seed_db():
    users = [
        User(name='Alice Guest', email='guest@hotel.com', role='guest'),
        User(name='Bob Reception', email='reception@hotel.com', role='reception'),
        User(name='Carol Staff', email='staff@hotel.com', role='service_staff'),
        User(name='Dave Admin', email='admin@hotel.com', role='admin'),
    ]
    users[0].set_password('guest123')
    users[1].set_password('staff123')
    users[2].set_password('staff123')
    users[3].set_password('admin123')
    for u in users:
        db.session.add(u)

    rooms = [
        Room(number='101', type='single', base_price=370, description='Cozy single room with city view'),
        Room(number='102', type='single', base_price=350, description='Cozy single room with garden view'),
        Room(number='201', type='double', base_price=580, description='Spacious double room with balcony'),
        Room(number='202', type='double', base_price=620, description='Double room with king bed'),
        Room(number='301', type='suite', base_price=1350, description='Luxury suite with living area and sea view'),
        Room(number='302', type='suite', base_price=1800, description='Presidential suite with private terrace'),
    ]
    for r in rooms:
        db.session.add(r)

    db.session.commit()
    print('Database seeded successfully!')


# Allow running directly: python seed.py
if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_db()
