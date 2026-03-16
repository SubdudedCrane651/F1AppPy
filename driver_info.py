# driver_info.py
import requests
from PyQt6 import QtWidgets, QtGui, QtCore


def fetch_image(url, timeout=5):
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            pix = QtGui.QPixmap()
            pix.loadFromData(resp.content)
            return pix
    except:
        return None
    return None


class DriverInfoWindow(QtWidgets.QWidget):
    def __init__(self, session, driver_code, driver_name, team_name, season):
        super().__init__()
        self.setWindowTitle(driver_name)
        self.resize(520, 720)

        main_layout = QtWidgets.QVBoxLayout()

        # Top row: flag, name, number
        top_row = QtWidgets.QHBoxLayout()

        self.flag_label = QtWidgets.QLabel()
        self.flag_label.setFixedSize(64, 40)
        self.flag_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        name_number_layout = QtWidgets.QVBoxLayout()
        self.driver_label = QtWidgets.QLabel(driver_name)
        self.driver_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.driver_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.number_label = QtWidgets.QLabel("")
        self.number_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.number_label.setStyleSheet("font-size: 16px;")
        name_number_layout.addWidget(self.driver_label)
        name_number_layout.addWidget(self.number_label)

        self.team_logo_label = QtWidgets.QLabel()
        self.team_logo_label.setFixedSize(80, 80)
        self.team_logo_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        top_row.addWidget(self.flag_label)
        top_row.addLayout(name_number_layout)
        top_row.addWidget(self.team_logo_label)

        # Driver portrait
        self.driver_img = QtWidgets.QLabel()
        self.driver_img.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.driver_img.setFixedHeight(260)

        # Car image
        self.car_img = QtWidgets.QLabel()
        self.car_img.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.car_img.setFixedHeight(220)

        # Team name
        self.team_label = QtWidgets.QLabel(team_name)
        self.team_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.team_label.setStyleSheet("font-size: 16px;")

        main_layout.addLayout(top_row)
        main_layout.addWidget(self.team_label)
        main_layout.addWidget(self.driver_img)
        main_layout.addWidget(self.car_img)

        self.setLayout(main_layout)

        self.load_images_and_info(session, driver_code, team_name, season)

    def load_images_and_info(self, session, driver_code, team_name, season):
        drv = session.get_driver(driver_code)

        # Driver portrait (FastF1)
        driver_url = drv.get("HeadshotUrl", None)

        # Team logo (FastF1 if available)
        team_logo_url = drv.get("TeamLogoUrl", None)

        # Car image (F1.com)
        team_slug = team_name.replace(" ", "-").lower()
        car_url = f"https://www.formula1.com/content/dam/fom-website/teams/{season}/{team_slug}.png"

        # Nationality flag (simple mapping via country code if available)
        country_code = drv.get("CountryCode", None)
        flag_url = None
        if country_code:
            # Simple flag CDN (e.g. flagcdn.com)
            flag_url = f"https://flagcdn.com/w80/{country_code.lower()}.png"

        # Driver number (text only)
        number = drv.get("PermanentNumber", None)
        if number:
            self.number_label.setText(f"#{number}")
        else:
            self.number_label.setText("")

        self.set_scaled_image(self.driver_img, driver_url, max_height=260)
        self.set_scaled_image(self.car_img, car_url, max_height=220)
        self.set_scaled_image(self.team_logo_label, team_logo_url, max_height=80)
        self.set_scaled_image(self.flag_label, flag_url, max_height=40)

    def set_scaled_image(self, label, url, max_height=260):
        if not url:
            label.setText("Image not available")
            return

        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                label.setText("Image not available")
                return

            pix = QtGui.QPixmap()
            pix.loadFromData(resp.content)

            # Correct scaling with aspect ratio preserved
            scaled = pix.scaled(
                label.width() if label.width() > 0 else max_height,
                max_height,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )

            label.setPixmap(scaled)

        except Exception:
            label.setText("Image not available")