import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from gstechou.models import School

class Command(BaseCommand):
    help = "Import school data from CSV file"

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
                # `school_type` のデフォルト設定（CSV にない場合は私立）
                school_type = row.get("school_type", "私立")
                if school_type not in ["私立", "国立"]:
                    school_type = "私立"  # 不正な値があった場合のデフォルト

                # `prefecture` のデフォルト設定（CSV にない場合は '不明'）
                prefecture = row.get("prefecture", "不明")
                if prefecture not in dict(School.PREFECTURE_CHOICES):
                    prefecture = "不明"  # 不正な値があった場合のデフォルト

                # 学校データを作成または更新
                School.objects.update_or_create(
                    name=row.get("name"),
                    defaults={
                        "address": row.get("address", ""),  # 住所がなければ空文字
                        "school_type": school_type,
                        "prefecture": prefecture,
                    },
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {count} 校のデータを追加しました！"))
