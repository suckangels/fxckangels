document.addEventListener("DOMContentLoaded", () => {
  // ===== typewriter =====
  const typeEl = document.getElementById("type");
  const lines = ["@fxckangels"];
  let i = 0, deleting = false;

  const speedType = 80;
  const speedDelete = 45;
  const pauseAfterType = 900;
  const pauseAfterDelete = 250;

  function tick(){
    const text = lines[0];
    if(!deleting){
      i++;
      typeEl.textContent = text.slice(0, i);
      if(i >= text.length){
        setTimeout(() => { deleting = true; tick(); }, pauseAfterType);
        return;
      }
      setTimeout(tick, speedType);
    } else {
      i--;
      typeEl.textContent = text.slice(0, i);
      if(i <= 0){
        deleting = false;
        setTimeout(tick, pauseAfterDelete);
        return;
      }
      setTimeout(tick, speedDelete);
    }
  }
  if (typeEl) tick();

  // ===== discord copy (super-robust) =====
  const discordBtn = document.getElementById("discordBtn");
  const DISCORD_TEXT = "coldangels";
  const ORIGINAL_TEXT = "discord";

  async function copyText(text){
    // 1) нормальный способ (только https/localhost)
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }

    // 2) fallback через execCommand
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      ta.style.top = "-9999px";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      if (ok) return true;
    } catch {}

    // 3) совсем жёсткий fallback — покажет текст, чтобы ты вручную скопировал
    prompt("Скопируй вручную:", text);
    return false;
  }

  if (discordBtn) {
    discordBtn.addEventListener("click", async () => {
      try {
        await copyText(DISCORD_TEXT);
        discordBtn.textContent = "copied!";
        setTimeout(() => discordBtn.textContent = ORIGINAL_TEXT, 1000);
      } catch (e) {
        console.error("Discord copy error:", e);
      }
    });
  } else {
    console.warn("discordBtn not found in DOM");
  }

  // ===== music + volume (super-robust) =====
  const audio = document.getElementById("bgm");
  const soundBtn = document.getElementById("soundBtn");
  const volume = document.getElementById("volume");

  if (!audio) console.warn("audio#bgm not found");
  if (!soundBtn) console.warn("button#soundBtn not found");
  if (!volume) console.warn("input#volume not found");

  const savedVol = localStorage.getItem("bgm_volume");
  const savedOn  = localStorage.getItem("bgm_on");

  if (audio && volume) {
    audio.volume = savedVol ? Number(savedVol) : Number(volume.value || 0.25);
    volume.value = String(audio.volume);

    volume.addEventListener("input", () => {
      audio.volume = Number(volume.value);
      localStorage.setItem("bgm_volume", String(audio.volume));
    });

    audio.addEventListener("error", () => {
      console.error("MP3 не загрузился. Проверь файл: site/assets/bg.mp3 (имя/путь).");
      if (soundBtn) soundBtn.textContent = "⚠";
    });
  }

  let isPlaying = false;

  function setIcon(){
    if (!soundBtn) return;
    soundBtn.textContent = isPlaying ? "🔊" : "🔇";
  }

  async function playAudio(){
    if (!audio) return;
    try{
      await audio.play();
      isPlaying = true;
      localStorage.setItem("bgm_on", "1");
    } catch (e){
      console.error("audio.play() заблокирован или упал:", e);
      isPlaying = false;
      localStorage.setItem("bgm_on", "0");
    }
    setIcon();
  }

  function pauseAudio(){
    if (!audio) return;
    audio.pause();
    isPlaying = false;
    localStorage.setItem("bgm_on", "0");
    setIcon();
  }

  if (soundBtn) {
    soundBtn.addEventListener("click", async () => {
      if (isPlaying) pauseAudio();
      else await playAudio();
    });
  }

  // если было включено ранее — попробуем включить при первом пользовательском действии
  if (savedOn === "1") {
    // показываем, что "включено", но реально стартанёт после клика/тапа
    isPlaying = false;
    if (soundBtn) soundBtn.textContent = "🔊";
    document.addEventListener("pointerdown", () => playAudio(), { once: true });
  } else {
    setIcon();
  }

  // ===== cursor effects (не обяз) =====
  if (window.cursoreffects?.fairyDustCursor) {
    window.cursoreffects.fairyDustCursor({ colors: ["#ffffff"] });
  }

  // ===== GSAP / Tilt (не обяз) =====
  if (window.gsap) {
    gsap.from(".panel, .avatarWrap", { opacity: 0, y: 18, duration: 0.9, stagger: 0.10, ease: "power2.out" });
  }
  if (window.VanillaTilt) {
    VanillaTilt.init(document.querySelectorAll(".card"), {
      max: 7, speed: 500, glare: false, scale: 1.01
    });
  }
});

