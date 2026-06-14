import os
import sys
from pathlib import Path
from dotenv import load_dotenv

class Settings:
    """项目全局配置 (单例模式)"""

    def __init__(self):
        # 项目根目录 (core/ 的父目录)
        self.PROJECT_ROOT = Path(__file__).parent.parent.resolve()

        # 确保项目根目录在 sys.path 中，以便各子模块能正确导入
        root_str = str(self.PROJECT_ROOT)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)

        # 加载 .env 文件
        env_path = self.PROJECT_ROOT / ".env"
        load_dotenv(env_path, encoding='utf-8')

        # =====================
        # 课程类型与打分模式配置
        # =====================
        # COURSE_TYPE: "animation" | "modeling"
        self.COURSE_TYPE = os.getenv("COURSE_TYPE", "animation").lower()
        # GRADING_MODE: "individual" | "group"
        self.GRADING_MODE = os.getenv("GRADING_MODE", "individual").lower()

        # =====================
        # 路径配置
        # =====================
        data_dir_raw = os.getenv("DATA_DIR", "data")
        data_dir_path = Path(data_dir_raw)
        if data_dir_path.is_absolute():
            self.DATA_DIR = data_dir_path.resolve()
        else:
            self.DATA_DIR = (self.PROJECT_ROOT / data_dir_path).resolve()

        # 作品根目录为 DATA_DIR 下的 "作品" 文件夹
        self.WORKS_ROOT_DIR = self.DATA_DIR / "作品"
        self.RESULT_DIR = self.DATA_DIR / "result"
        self.LOG_FILE = self.RESULT_DIR / "grading.log"
        self.THUMBNAIL_CACHE_DIR = self.DATA_DIR / "thumbnail_cache"
        self.GRADING_RESULTS_JSON = self.RESULT_DIR / "grading_results.json"

        # 自动在 RESULT_DIR 下寻找 Excel 文件 (排除隐藏临时文件 ~$...)
        self.EXCEL_FILENAME = None
        self.EXCEL_PATH = None
        
        if self.RESULT_DIR.exists():
            for f in self.RESULT_DIR.glob("*.xlsx"):
                if not f.name.startswith("~$"):
                    self.EXCEL_FILENAME = f.name
                    self.EXCEL_PATH = f
                    break
                    
        # 兜底：如果没找到，就使用默认名
        if not self.EXCEL_FILENAME:
            self.EXCEL_FILENAME = "评分记录表.xlsx"
            self.EXCEL_PATH = self.RESULT_DIR / self.EXCEL_FILENAME

        # =====================
        # 评分行为配置
        # =====================
        self.ENABLE_LLM_GRADING = os.getenv("ENABLE_LLM_GRADING", "true").lower() == "true"

        # 视频文件配置 (主要用于动画)
        self.VIDEO_EXTENSIONS = [".mkv", ".mp4", ".mov", ".avi"]

        # =====================
        # 批处理子目录
        # =====================
        self.BATCH_GRADER_DIR = self.PROJECT_ROOT / "batch_grader"
        self.STUDENT_WEB_DIR = self.PROJECT_ROOT / "student_web"

# 全局单例
settings = Settings()
