import sys
import csv
from app import app
from models import db, Annot

def export_data():
    """
    データベース内のすべてのアノテーションデータをCSV形式で標準出力に出力します。
    """
    with app.app_context():
        # データベースからすべてのアノテーションを取得
        annotations = Annot.query.all()

        if not annotations:
            print("アノテーションデータが見つかりません。", file=sys.stderr)
            return

        # CSVライターを標準出力に設定
        writer = csv.writer(sys.stdout)

        # ヘッダー行を書き込む
        header = [
            'id', 
            'video_path', 
            'sign', 
            'user', 
            'time', 
            'label', 
            'comments'
        ]
        writer.writerow(header)

        # 各アノテーションデータを書き込む
        for annot in annotations:
            writer.writerow([
                annot.id,
                annot.video_path,
                annot.sign,
                annot.user,
                annot.time.isoformat(),
                annot.label,
                annot.comments
            ])

if __name__ == "__main__":
    export_data()