from app import create_app
from app.models import User, AuditLog

app = create_app()

with app.app_context():
    print("USERS")
    for u in User.query.all():
        print(u.user_id, u.name, u.email, u.role, u.password_hash[:30] + "...")

    print()
    print("AUDIT LOG")
    for log in AuditLog.query.order_by(AuditLog.log_id).all():
        print(log.log_id, log.user_id, log.action, log.timestamp)