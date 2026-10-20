"""Playwright bot for The Crims Hunting Grounds.

Log in manually when prompted.  The script only attacks occupants whose visible
name contains ``[bot]``; a real player's slot is never clicked.
"""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


# --- Game settings ---------------------------------------------------------
MAX_ASSAULTS = 0  # 0 = run until stopped with Ctrl+C
STAMINA_REFILL_THRESHOLD = 25
CLUB_WAIT_SECONDS = 7.0


# --- Verified selectors (2026-08-05) -------------------------------------
MENU_ASSAULT = "#menu-assault-areas"
MENU_HUNTING_GROUNDS = "#menu-the-hunting-grounds"

CLUBS = "#nightlife-nightclubs > div.grid > div.well"
CLUB_NAME = ":scope > div:first-child > div.font-bold"
CLUB_ASSAULT_POWER = ":scope > div:first-child > div:nth-of-type(3)"
CLUB_ENTER = ":scope > button"
HUNTING_REFRESH = "#hunting-grounds-refresh"

MY_ASSAULT_POWER = '#robbery-powers > div:has(> strong:text-is("AP")) > .animated-stat'

HP_BAR = 'div[class*="_hp_"]'
STAMINA_BAR = 'div[class*="_stamina_"]'
PROGRESS_TEXT = 'div[class*="_progressBarText_"]'
REFILL_STAMINA = "#robbery-stamina-refill"

SLOTS = "div.front-well-text.bg-image.bg-assaults-image > div.grid.grid-cols-2 > div"
EMPTY_SLOT = 'img[alt="placeholder_avatar"]'
OCCUPANT = ".visitor_information"
OCCUPANT_NAME = ".user_list_username"
OCCUPANT_CLASS_AND_LEVEL = ".text-xs:first-of-type"
OCCUPANT_RESPECT = '.text-xs:has-text("Respect:")'
CHOOSE = 'button:has-text("[Choose...]")'
SINGLE_ASSAULT = 'button:has-text("Single assault")'
ATTACK = 'button:has-text("Attack")'


class HumanMouse:
    """Moves through a short eased path, shows a red cursor dot, then clicks."""

    def __init__(self) -> None:
        self.last_x = 200.0
        self.last_y = 200.0

    @staticmethod
    def ensure_cursor_dot(page: Page) -> None:
        page.evaluate(
            """() => {
                if (document.getElementById('bot-cursor-dot')) return;
                const dot = document.createElement('div');
                dot.id = 'bot-cursor-dot';
                dot.style.cssText = `position:fixed;left:0;top:0;width:12px;height:12px;
                    background:red;border:2px solid white;border-radius:50%;pointer-events:none;
                    z-index:2147483647;box-shadow:0 0 10px rgba(255,0,0,.8)`;
                document.body.appendChild(dot);
            }"""
        )

    @staticmethod
    def _move_dot(page: Page, x: float, y: float) -> None:
        page.evaluate(
            """({x, y}) => {
                const dot = document.getElementById('bot-cursor-dot');
                if (dot) { dot.style.left = x + 'px'; dot.style.top = y + 'px'; }
            }""",
            {"x": x, "y": y},
        )

    @staticmethod
    def _pulse_dot(page: Page) -> None:
        page.evaluate(
            """() => {
                const dot = document.getElementById('bot-cursor-dot');
                if (!dot) return;
                dot.animate([{transform:'scale(1)'},{transform:'scale(1.6)'},{transform:'scale(1)'}],
                    {duration:180, easing:'ease-out'});
                dot.style.background = 'lime';
                setTimeout(() => dot.style.background = 'red', 200);
            }"""
        )

    def click_locator(self, page: Page, locator: Locator, *, jitter: int = 7) -> bool:
        """Click the locator's centre by coordinates; never calls locator.click()."""
        try:
            locator.wait_for(state="visible", timeout=3_000)
            locator.scroll_into_view_if_needed(timeout=3_000)
        except PlaywrightTimeoutError:
            return False

        box = locator.bounding_box()
        if box is None:
            return False

        target_x = box["x"] + box["width"] * 0.50 + random.randint(-jitter, jitter)
        target_y = box["y"] + box["height"] * 0.45 + random.randint(-jitter, jitter)
        self.ensure_cursor_dot(page)

        steps = random.randint(15, 25)
        for step in range(steps + 1):
            t = step / steps
            eased = t * t * (3.0 - 2.0 * t)
            x = self.last_x + (target_x - self.last_x) * eased
            y = self.last_y + (target_y - self.last_y) * eased
            page.mouse.move(x, y, steps=1)
            self._move_dot(page, x, y)
            time.sleep(random.uniform(0.005, 0.015))

        self.last_x, self.last_y = target_x, target_y
        self._pulse_dot(page)
        page.mouse.click(target_x, target_y)
        time.sleep(random.uniform(0.10, 0.25))
        return True


@dataclass(frozen=True)
class Club:
    index: int
    name: str
    assault_power: int


def parse_number(text: str) -> int:
    match = re.search(r"[\d,]+", text.replace("\xa0", " "))
    if not match:
        raise ValueError(f"No number in: {text!r}")
    return int(match.group(0).replace(",", ""))


def read_fraction(page: Page, bar_selector: str) -> tuple[int, int] | None:
    """Reads a progress bar as (current, maximum), e.g. (945, 1000)."""
    bar = page.locator(bar_selector)
    if bar.count() != 1:
        return None
    text = (bar.locator("..").text_content() or "").replace("\xa0", " ")
    match = re.search(r"([\d,]+)\s*/\s*([\d,]+)", text)
    if not match:
        return None
    return int(match.group(1).replace(",", "")), int(match.group(2).replace(",", ""))


def read_stamina(page: Page) -> tuple[int, int] | None:
    return read_fraction(page, STAMINA_BAR)


def read_hp(page: Page) -> tuple[int, int] | None:
    return read_fraction(page, HP_BAR)


def read_my_assault_power(page: Page) -> int | None:
    value = page.locator(MY_ASSAULT_POWER)
    if value.count() != 1:
        return None
    try:
        return parse_number(value.inner_text())
    except ValueError:
        return None


def open_hunting_grounds(page: Page, mouse: HumanMouse) -> bool:
    """Opens Assault -> Hunting Grounds unless the card list is already visible."""
    if page.locator(CLUBS).count() == 8:
        return True
    if not mouse.click_locator(page, page.locator(MENU_ASSAULT)):
        return False
    try:
        page.locator(MENU_HUNTING_GROUNDS).wait_for(state="visible", timeout=5_000)
    except PlaywrightTimeoutError:
        return False
    if not mouse.click_locator(page, page.locator(MENU_HUNTING_GROUNDS)):
        return False
    try:
        page.locator(CLUBS).first.wait_for(state="visible", timeout=5_000)
        return True
    except PlaywrightTimeoutError:
        return False


def get_eligible_club(page: Page, my_ap: int) -> Club | None:
    cards = page.locator(CLUBS)
    for index in range(cards.count()):
        card = cards.nth(index)
        try:
            club_ap = parse_number(card.locator(CLUB_ASSAULT_POWER).inner_text())
            name = card.locator(CLUB_NAME).inner_text().strip()
        except (PlaywrightTimeoutError, ValueError):
            continue
        if club_ap < my_ap:
            return Club(index=index, name=name, assault_power=club_ap)
    return None


def enter_club(page: Page, mouse: HumanMouse, club: Club) -> bool:
    card = page.locator(CLUBS).nth(club.index)
    if not mouse.click_locator(page, card.locator(CLUB_ENTER)):
        return False
    try:
        page.locator(SLOTS).first.wait_for(state="visible", timeout=5_000)
        return True
    except PlaywrightTimeoutError:
        return False


def scan_and_attack_bot(page: Page, mouse: HumanMouse) -> bool:
    """Waits up to seven seconds; attacks only a name containing '[bot]'."""
    deadline = time.monotonic() + CLUB_WAIT_SECONDS
    while time.monotonic() < deadline:
        slots = page.locator(SLOTS)
        for index in range(slots.count()):
            slot = slots.nth(index)
            if slot.locator(EMPTY_SLOT).count() > 0:
                continue

            occupant = slot.locator(OCCUPANT)
            if occupant.count() != 1:
                continue
            name = (occupant.locator(OCCUPANT_NAME).text_content() or "").strip()
            if not name:
                continue
            if "[bot]" not in name.lower():
                print(f"Pomijam prawdziwego gracza: {name}")
                continue

            class_and_level = (occupant.locator(OCCUPANT_CLASS_AND_LEVEL).text_content() or "").strip()
            respect = (occupant.locator(OCCUPANT_RESPECT).text_content() or "").strip()
            print(f"Bot: {name} | {class_and_level} | {respect}")

            choose = slot.locator(CHOOSE)
            if not mouse.click_locator(page, choose):
                continue
            try:
                single = slot.locator(SINGLE_ASSAULT)
                single.wait_for(state="visible", timeout=1_500)
            except PlaywrightTimeoutError:
                continue
            if not mouse.click_locator(page, single):
                continue

            try:
                attack = slot.locator(ATTACK)
                attack.wait_for(state="visible", timeout=1_500)
            except PlaywrightTimeoutError:
                continue

            # Single assault costs 10 HP.  Check immediately before the final
            # external action, because HP may have changed while the menu opened.
            hp = read_hp(page)
            if hp is None:
                print("Nie można odczytać HP: pomijam ATTACK dla bezpieczeństwa.")
                return False
            if hp[0] < 10:
                print(f"HP={hp[0]}/{hp[1]} (<10): nie klikam ATTACK.")
                return False

            return mouse.click_locator(page, attack)

        page.wait_for_timeout(250)
    return False


def refill_if_needed(page: Page, mouse: HumanMouse) -> bool:
    stamina = read_stamina(page)
    if stamina is None or stamina[0] >= STAMINA_REFILL_THRESHOLD:
        return False
    print(f"Stamina {stamina[0]}/{stamina[1]}: używam Refill Stamina.")
    return mouse.click_locator(page, page.locator(REFILL_STAMINA))


def refresh_clubs_after_attack(page: Page, mouse: HumanMouse) -> bool:
    """After an attack, refresh only Hunting Grounds' club list."""
    refresh = page.locator(HUNTING_REFRESH)
    try:
        refresh.wait_for(state="visible", timeout=5_000)
    except PlaywrightTimeoutError:
        print("Nie pojawił się przycisk odświeżania klubów po ataku.")
        return False

    if not mouse.click_locator(page, refresh):
        return False
    page.wait_for_timeout(800)
    return True


def run() -> None:
    mouse = HumanMouse()
    completed = 0

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()
        page.goto("https://www.thecrims.com/", wait_until="domcontentloaded")
        mouse.ensure_cursor_dot(page)
        input("Zaloguj się ręcznie, a potem naciśnij Enter w konsoli... ")

        try:
            while MAX_ASSAULTS == 0 or completed < MAX_ASSAULTS:
                if not open_hunting_grounds(page, mouse):
                    print("Nie udało się otworzyć Hunting Grounds. Ponawiam.")
                    page.wait_for_timeout(1_000)
                    continue

                hp = read_hp(page)
                stamina = read_stamina(page)
                my_ap = read_my_assault_power(page)
                print(f"HP={hp} | Stamina={stamina} | AP={my_ap}")
                if my_ap is None:
                    print("Nie można odczytać Assault Power postaci.")
                    page.wait_for_timeout(1_000)
                    continue
                if refill_if_needed(page, mouse):
                    page.wait_for_timeout(1_000)
                    continue

                club = get_eligible_club(page, my_ap)
                if club is None:
                    print("Brak klubu z AP niższym od własnego: odświeżam wyłącznie listę klubów.")
                    mouse.click_locator(page, page.locator(HUNTING_REFRESH))
                    page.wait_for_timeout(800)
                    continue

                print(f"Wchodzę: {club.name}, AP klubu {club.assault_power} < {my_ap}.")
                if not enter_club(page, mouse, club):
                    print("Wejście do klubu nie potwierdziło się.")
                    page.wait_for_timeout(500)
                    continue

                if scan_and_attack_bot(page, mouse):
                    completed += 1
                    print(f"Wysłano Attack. Wykonane ataki: {completed}")
                    if refresh_clubs_after_attack(page, mouse):
                        print("Odświeżono listę klubów po ataku.")
                else:
                    print("W tej rundzie nie znaleziono bota do bezpiecznego ataku.")
                page.wait_for_timeout(1_000)
        except KeyboardInterrupt:
            print("Zatrzymano przez użytkownika.")
        finally:
            browser.close()


if __name__ == "__main__":
    run()
