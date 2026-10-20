import time
import random
import re
from playwright.sync_api import sync_playwright, Page, Locator

# ==============================================================================
# KONFIGURACJA SELEKTORÓW I WARTOŚCI
# ==============================================================================

# Progi
STAMINA_ACTION_THRESHOLD = 250  # 25% z obecnego maksimum 1000
ADDICTION_MAX_THRESHOLD = 80    # Uzależnienie, przy którym idziemy na odwyk

# Selektory
SELECTOR_STAMINA_TEXT = r"^\s*\d{1,3}%\s*$"
SELECTOR_STAMINA_BAR = 'div[class*="_stamina_"]'
SELECTOR_GANG_ACCEPT = "#gangrobbery-accept"
SELECTOR_GANG_EXECUTE = "#gangrobbery-execute"

# ==============================================================================
# KLASA MYSZKI (Logic from bot.py)
# ==============================================================================

class HumanMouse:
    def __init__(self):
        self.last_x = 200.0
        self.last_y = 200.0

    def ensure_cursor_dot(self, page: Page):
        page.evaluate("""
            () => {
                if (document.getElementById('bot-cursor-dot')) return;
                const dot = document.createElement('div');
                dot.id = 'bot-cursor-dot';
                dot.style.cssText = `
                    position: fixed; left: 0px; top: 0px; width: 12px; height: 12px;
                    background: red; border: 2px solid white; border-radius: 50%;
                    pointer-events: none; z-index: 2147483647;
                    box-shadow: 0 0 10px rgba(255,0,0,0.8);
                `;
                document.body.appendChild(dot);
            }
        """)

    def move_dot(self, page: Page, x: float, y: float):
        page.evaluate("""
            ({ x, y }) => {
                const dot = document.getElementById('bot-cursor-dot');
                if (!dot) return;
                dot.style.left = x + 'px';
                dot.style.top = y + 'px';
            }
        """, {"x": x, "y": y})

    def pulse_dot(self, page: Page, color: str):
        page.evaluate("""
            (color) => {
                const dot = document.getElementById('bot-cursor-dot');
                if (!dot) return;
                dot.animate(
                    [{ transform: 'scale(1)' }, { transform: 'scale(1.6)' }, { transform: 'scale(1)' }],
                    { duration: 180, easing: 'ease-out' }
                );
                dot.style.background = color;
                setTimeout(() => { dot.style.background = 'red'; }, 200);
            }
        """, color)

    def move_and_click(self, page: Page, target_x: float, target_y: float, jitter: int = 8):
        self.ensure_cursor_dot(page)
        target_x += random.randint(-jitter, jitter)
        target_y += random.randint(-jitter, jitter)
        
        start_x, start_y = self.last_x, self.last_y
        steps = random.randint(15, 25)  # Szybszy ruch (było 18-35)
        
        for i in range(steps + 1):
            t = i / steps
            eased = t * t * (3.0 - 2.0 * t)
            x = start_x + (target_x - start_x) * eased
            y = start_y + (target_y - start_y) * eased
            
            page.mouse.move(x, y, steps=1)
            self.move_dot(page, x, y)
            time.sleep(random.uniform(0.005, 0.015)) # Szybsze kroki
        
        self.last_x, self.last_y = target_x, target_y
        self.pulse_dot(page, "lime")
        page.mouse.click(target_x, target_y)
        time.sleep(random.uniform(0.1, 0.25)) # Krótsza pauza po kliku

    def click_locator(self, page: Page, loc: Locator, jitter: int = 10, do_scroll: bool = True):
        # Timeout zmniejszony, żeby szybciej wykrywał błędy/zmiany
        try:
            loc.wait_for(state="visible", timeout=3000) 
        except:
            pass # Nie rzucaj błędem, jeśli element zniknie (dynamiczne UI)

        if do_scroll:
            try:
                loc.scroll_into_view_if_needed()
            except Exception:
                pass
        
        box = loc.bounding_box()
        if not box:
            # Czasami bounding box zwraca None, mimo że element jest. Spróbujmy jeszcze raz.
            time.sleep(0.1)
            box = loc.bounding_box()
            if not box:
                # print("⚠️ Element niewidoczny (brak boxa).") # Mniej spamu
                return
        
        cx = box["x"] + box["width"] * 0.50
        cy = box["y"] + box["height"] * 0.35
        self.move_and_click(page, cx, cy, jitter)

mouse = HumanMouse()

# ==============================================================================
# FUNKCJE CZYTAJĄCE STAN
# ==============================================================================

def read_percent_value(page: Page, regex_pattern: str, nth_index: int = 1) -> int | None:
    try:
        loc = page.locator("div").filter(has_text=re.compile(regex_pattern)).nth(nth_index)
        if loc.count() == 0:
            return None
        txt = (loc.text_content() or "").strip()
        m = re.search(r"(\d+)", txt)
        return int(m.group(1)) if m else None
    except Exception:
        return None

def read_stamina(page: Page) -> int | None:
    """Zwraca aktualną staminę z formatu np. ``876 / 1000``."""
    try:
        bar = page.locator(SELECTOR_STAMINA_BAR)
        if bar.count() != 1:
            return None
        text = (bar.locator("..").text_content() or "").replace("\xa0", " ")
        match = re.search(r"([\d,]+)\s*/\s*([\d,]+)", text)
        return int(match.group(1).replace(",", "")) if match else None
    except Exception:
        return None

def read_addiction(page: Page) -> int | None:
    try:
        el = page.locator('div[class*="_addiction_"]').first
        if el.count() > 0:
            txt = el.text_content() or ""
            m = re.search(r"(\d+)%", txt)
            if m: return int(m.group(1))
            
            parent_txt = el.locator("..").text_content() or ""
            m_parent = re.search(r"(\d+)%", parent_txt)
            if m_parent: return int(m_parent.group(1))
    except Exception:
        pass
    
    # Fallback
    try:
        locs = page.locator("div").filter(has_text=re.compile(r"^\s*\d+%\s*$"))
        if locs.count() > 0:
            pass 
    except:
        pass

    return None

# ==============================================================================
# AKCJE GRY
# ==============================================================================

def perform_detox(page: Page):
    print("🚑 UZALEŻNIENIE WYSOKIE! Jadę na odwyk...")
    try:
        menu_services = page.locator("#menu-city-services")
        mouse.click_locator(page, menu_services)
        time.sleep(random.uniform(1.0, 1.5))
        
        hospital_btn = page.get_by_text("Hospital")
        mouse.click_locator(page, hospital_btn)
        time.sleep(random.uniform(1.0, 1.5))
        
        buy_btn = page.get_by_role("button", name="Buy for $")
        if buy_btn.count() > 0:
            mouse.click_locator(page, buy_btn.first)
            print("✅ Odwyk kupiony.")
            time.sleep(random.uniform(1.0, 2.0))
        else:
            print("⚠️ Nie widzę przycisku 'Buy for $' w szpitalu.")

        print("🔙 Wracam do zakładki Robbery...")
        menu_robbery = page.locator("#menu-robbery")
        mouse.click_locator(page, menu_robbery)
        time.sleep(random.uniform(1.5, 2.5))
    except Exception as e:
        print(f"⚠️ Błąd podczas odwyku: {e}")

def refill_stamina(page: Page):
    print("⚡ STAMINA LOW (<25%) -> Refill...")
    try:
        refill_btn = page.locator("#robbery-stamina-refill")
        
        if refill_btn.count() > 0:
            mouse.click_locator(page, refill_btn.first)
            print("✅ Stamina odnowiona.")
            time.sleep(random.uniform(1.0, 1.5))
        else:
            print("⚠️ Nie znaleziono przycisku Refill Stamina.")
    except Exception as e:
         print(f"⚠️ Błąd refilla: {e}")

def do_the_score_sequence(page: Page) -> bool:
    """Wersja szybka: klika Accept, a potem agresywnie szuka 'Do the score'."""
    
    # 1. Kliknij Accept
    accept_btn = page.locator(SELECTOR_GANG_ACCEPT)
    if accept_btn.count() > 0:
        mouse.click_locator(page, accept_btn.first)
        print("✅ Kliknięto Accept. Czekam na Do the score...")
        
        # 2. Pętla oczekiwania na "Do the score!" (Max 10 sekund)
        max_retries = 20  # 20 prób * ~0.5s = ok. 10 sekund
        for i in range(max_retries):
            score_btn = page.locator(SELECTOR_GANG_EXECUTE)
            
            # Sprawdź czy przycisk jest widoczny (szybki check)
            if score_btn.count() > 0 and score_btn.first.is_visible():
                # Kliknij od razu!
                mouse.click_locator(page, score_btn.first, jitter=5) # Mniejszy jitter = szybciej
                print("✅ Napad wykonany (Do the score).")
                time.sleep(random.uniform(0.5, 1.0)) # Krótki odpoczynek po kliku
                return True
            
            # Jeśli nie ma, czekaj chwilę i spróbuj ponownie (odświeżanie logiki)
            # Używamy randoma, żeby nie było idealnie co 500ms (ochrona przed detekcją)
            time.sleep(random.uniform(0.4, 0.7))
        
        print("⚠️ Timeout: Przycisk 'Do the score!' nie pojawił się przez 10s.")
        return False
        
    else:
        # Czasami przycisku Accept nie ma, bo od razu jest Do the score? (np. po refreshu)
        score_btn = page.locator(SELECTOR_GANG_EXECUTE)
        if score_btn.count() > 0 and score_btn.first.is_visible():
             mouse.click_locator(page, score_btn.first, jitter=5)
             print("✅ Napad wykonany (Bez Accept).")
             time.sleep(random.uniform(0.5, 1.0))
             return True
             
        print("⚠️ Nie widzę przycisku 'Accept' ani 'Do the score'.")
        return False

# ==============================================================================
# GŁÓWNA PĘTLA
# ==============================================================================

def run_bot():
    # --- INPUT UŻYTKOWNIKA ---
    print("-" * 40)
    user_input = input("🔢 Podaj liczbę rabunków do wykonania (0 lub puste = nieskończoność): ").strip()
    try:
        MAX_ROBBERIES = int(user_input)
    except ValueError:
        MAX_ROBBERIES = 0
    
    limit_desc = "NIESKOŃCZONOŚĆ" if MAX_ROBBERIES == 0 else str(MAX_ROBBERIES)
    print(f"⚙️ Ustawiono limit: {limit_desc}")
    print("-" * 40)
    # -------------------------

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("🚀 Otwieram The Crims...")
        page.goto("https://www.thecrims.com/")
        
        mouse.ensure_cursor_dot(page)
        
        input("🔑 Zaloguj się ręcznie, wejdź w zakładkę ROBBERY i naciśnij ENTER tutaj w konsoli...")
        print("🟢 BOT STARTUJE")

        robberies_done = 0

        while True:
            try:
                # Sprawdzenie limitu
                if MAX_ROBBERIES > 0 and robberies_done >= MAX_ROBBERIES:
                    print(f"🏁 Osiągnięto limit {MAX_ROBBERIES} rabunków. Koniec pracy.")
                    break

                stamina = read_stamina(page)
                addiction = read_addiction(page)
                
                # Wyświetl status + licznik
                add_str = f"{addiction}%" if addiction is not None else "?"
                st_str = f"{stamina}/1000" if stamina is not None else "?"
                progress_str = f"{robberies_done}/{limit_desc}"
                
                print(f"📊 Status: Stamina={st_str} | Addiction={add_str} | Rabunki: {progress_str}")

                # LOGIKA: UZALEŻNIENIE
                if addiction is not None and addiction >= ADDICTION_MAX_THRESHOLD:
                    perform_detox(page)
                    continue 

                # LOGIKA: STAMINA
                if stamina is not None:
                    # 0% - 24% -> Refill
                    if stamina < STAMINA_ACTION_THRESHOLD:
                        refill_stamina(page)
                    
                    # 25% - 100% -> Napad
                    else:
                        if do_the_score_sequence(page):
                            robberies_done += 1
                        
                else:
                    print("⚠️ Nie mogę odczytać staminy.")
                    time.sleep(1) # Szybszy retry przy błędzie odczytu

                # Krótka pauza pętli
                time.sleep(random.uniform(0.5, 1.2)) # Szybsza pętla główna (było 1.0-2.0)

            except KeyboardInterrupt:
                print("🛑 Zatrzymano bota.")
                break
            except Exception as e:
                print(f"⚠️ Błąd pętli: {e}")
                time.sleep(3)

        browser.close()

if __name__ == "__main__":
    run_bot()
