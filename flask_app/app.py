import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Annot, User
from config import Config, DBLogin
from datetime import datetime
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "https://annotation2.utokyo-jsl.org", "https://backend2.utokyo-jsl.org"]}})

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DBLogin.USER}:{DBLogin.PSWD}@localhost/labels'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)


with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return "Flask is running"

@app.route('/add_annot', methods=['POST'])
def add_annot():
    data = request.json
    if not User.query.filter_by(username=data["user"]).first():
        return jsonify({"error": "User not found"}), 403
    data = request.json
    cmd = insert(Annot).values(
        sign=data['sign'],
        user=data["user"],
        label=data["label"],
        comments=data.get('comments', ""),
        time=datetime.fromtimestamp(data["time"] / 1000),
        video_path=os.path.basename(data["video_path"])
    ).on_duplicate_key_update(
        sign=data['sign'],
        label=data["label"],
        comments=data.get('comments', ""),
        time=datetime.fromtimestamp(data["time"] / 1000)
    )

    try:
        db.session.execute(cmd)
        db.session.commit()
        return jsonify({"message": "Added annotation"})
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Failed to add annotation"}), 500
    
@app.route('/check_user', methods=['POST'])
def check_user():
    from models import db, User
    data = request.json
    username = data.get("username")

    user = db.session.execute(
        db.select(User).filter_by(username=username)
    ).scalar()

    if user:
        return jsonify({"valid": True})
    else:
        return jsonify({"valid": False})

@app.route('/check_annotations', methods=['POST'])
def check_annotations():
    """
    ビデオパスのリストを受け取り、DB内で注釈が存在するパスのリストを返す。
    """
    data = request.json
    video_paths_to_check = data.get('video_paths', [])

    if not video_paths_to_check:
        return jsonify({"annotated_paths": []})

    # 提供されたビデオパスのうち、DBに存在するものだけを問い合わせる
    query = db.select(db.distinct(Annot.video_path)).where(Annot.video_path.in_(video_paths_to_check))
    
    # .scalars().all() を使って結果をPythonのリストとして取得
    annotated_paths = db.session.execute(query).scalars().all()
    print(annotated_paths)

    return jsonify({"annotated_paths": annotated_paths})


if __name__ == '__main__':
    app.run(debug=True)
