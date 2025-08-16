from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_login import LoginManager, login_required
import os
from config.settings import config
from models.notification import notification_manager
from models.auth import User, init_db
from api.auth_route import auth_bp
from api.metrics_route import metrics_bp
from api.monitor_route import monitor_bp
from api.notification_route import notification_bp
from api.websocket_handlers import register_socketio_events
from services.streaming.streaming_service import initialize_streaming_service

app = Flask(__name__)
app.config['SECRET_KEY'] = '23ysE&^!(*hqd88q7d8qdjhqe&(S^QW(69q7y6edqdq89dy7hqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(config.DATABASE_PATH)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

os.makedirs(os.path.dirname(config.MONITOR_RECORDINGS_DIR), exist_ok=True)
os.makedirs(os.path.dirname(config.SNAPSHOTS_DIR), exist_ok=True)
os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(config.YOLO_MODEL_PATH), exist_ok=True)
os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)


# Initialize authentication
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login' # type: ignore
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(metrics_bp)
app.register_blueprint(monitor_bp)
app.register_blueprint(notification_bp)

# Import and register active users blueprint
from api.active_users_route import active_users_bp
app.register_blueprint(active_users_bp)

# Initialize databases (notification manager first, then auth)
notification_manager.init_app(app)
init_db(app)

# Context processor to make current user available in templates
@app.context_processor
def inject_user():
    from flask_login import current_user
    return dict(current_user=current_user)

# Disable OpenCV preview for web streaming
setattr(config, "SHOW_PREVIEW", False)

# Initialize services
streaming_service = initialize_streaming_service(socketio)

# Register WebSocket events
register_socketio_events(socketio)

# Initialize and start all components with error handling
try:
    # Check if we should run in auth-only mode (for testing without RTSP)
    auth_only_mode = os.getenv('AUTH_ONLY_MODE', 'false').lower() == 'true'
    
    if not auth_only_mode:
        print("[INFO] Starting RTSP Baby Monitor Streamer...")
        
        if streaming_service.initialize():
            streaming_service.start()
            print("[INFO] All streaming components started successfully")
        else:
            print("[WARNING] Failed to initialize streaming components")
            print("[INFO] Running in Authentication-Only Mode")
    else:
        print("[INFO] Running in Authentication-Only Mode (RTSP disabled)")
        print("[INFO] Set AUTH_ONLY_MODE=false to enable RTSP streaming")
        
except Exception as e:
    print(f"[WARNING] Failed to initialize streaming components: {e}")
    print("[INFO] Running in Authentication-Only Mode")
    print("[INFO] You can still access user management and authentication features")


@app.route('/')
@login_required
def index():
    return render_template('dashboard.html')

#health check endpoint
@app.route('/health')
def health_check():
    return {"status": "healthy"}, 200


if __name__ == '__main__':
    # Production-ready configuration with WebSocket support
    socketio.run(app, 
                host='0.0.0.0', 
                port=8847, 
                debug=True,  # Disabled for production
                use_reloader=False,
                allow_unsafe_werkzeug=True)