import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from gstechou.models import School

class Command(BaseCommand):
    help = "Import private school data from CSV file"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file")

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        if not os.path.exists(csv_file):
            self.stderr.write(self.style.ERROR(f"File '{csv_file}' not found."))
            return

        # CSV を読み込む
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                # `school_type` を「私立」に固定
                school_type = "私立"

                # `prefecture` のデフォルト設定（不正な値を防ぐ）
                prefecture = row.get("prefecture", "不明")
                if prefecture not in dict(School.PREFECTURE_CHOICES):
                    prefecture = "不明"

                # 学校データを作成または更新
                School.objects.update_or_create(
                    name=row.get("name"),
                    defaults={
                        "address": row.get("address", ""),  # 住所がなければ空にする
                        "school_type": school_type,
                        "prefecture": prefecture,
                    },
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {count} 校のデータを追加しました！"))
