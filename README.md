# Miflon

[![Lisans](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Sürüm](https://img.shields.io/github/v/release/stilkod/Miflon)](https://github.com/stilkod/Miflon/releases)
[![İndirmeler](https://img.shields.io/github/downloads/stilkod/Miflon/total.svg)](https://github.com/stilkod/Miflon/releases)

**Miflon, görsellerinizdeki hassas verileri kolayca gizlemek, kırpmak ve yeniden boyutlandırmak için tasarlanmış, hızlı ve güçlü bir masaüstü aracıdır.**

Karmaşık fotoğraf düzenleme yazılımlarında kaybolmadan, en sık ihtiyaç duyulan işlemleri saniyeler içinde gerçekleştirin. Miflon ile görsellerinizi güvenle ve hızla paylaşıma hazır hale getirin!

![Miflon Arayüzü Ekran Görüntüsü](assets/screenshot.gif) <!-- ÖNEMLİ: UYGULAMANIZIN EKRAN GÖRÜNTÜSÜNÜ VEYA GIF'İNİ BURAYA EKLEYİN -->

## ✨ Ana Özellikler

*   **Hassas İçerik Gizleme:** Tek bir fare hareketiyle seçtiğiniz alanları **Bulanıklaştırma (Blur)** veya **Pikselleştirme (Pixelate)** efektleriyle anında sansürleyin.
*   **Esnek Seçim Araçları:** Efekt uygulamak için **Dörtgen** veya **Yuvarlak (Oval)** alanlar seçin.
*   **Ayarlanabilir Efekt Şiddeti:** Uygulayacağınız bulanıklık veya piksel boyutunu bir kaydırma çubuğu ile kolayca kontrol edin.
*   **Gelişmiş Kırpma:** Görsellerinizi **21:9 (Manşet)**, **16:9 (Galeri)**, **4:3 (Klasik)** ve **1:1 (Kare)** gibi popüler oranlara göre, canlı ve interaktif önizleme ile kolayca kırpın.
*   **Akıllı Yeniden Boyutlandırma:** Orijinal en-boy oranını koruyarak görsellerinizi önceden tanımlanmış (Küçük, Orta, Büyük) veya özel boyutlara getirin.
*   **Kalite Kontrolü:** Kayıt sırasında JPG kalitesini ayarlayarak dosya boyutu ve görüntü netliği arasında mükemmel dengeyi kurun.
*   **Geri Alma Desteği:** `Ctrl+Z` kısayolu veya "Geri Al" butonu ile yaptığınız değişiklikleri kolayca geri alın.
*   **Duyarlı Arayüz:** Uygulama penceresi, farklı ekran boyutlarına uyum sağlar ve görseli her zaman merkezde tutar.

## 🚀 Başlarken

### 1. Kullanıcılar için (En Kolay Yol)

Uygulamayı kullanmak için Python veya herhangi bir kütüphane kurmanıza gerek yok!

1.  Projenin [**Releases**](https://github.com/stilkod/Miflon/releases) sayfasına gidin.
2.  En son sürümün altındaki `Miflon.exe` (Windows için) dosyasını indirin.
3.  İndirdiğiniz dosyayı çalıştırın. Hepsi bu kadar!

### 2. Geliştiriciler için (Kaynaktan Kurulum)

Projeye katkıda bulunmak veya kodu kendiniz çalıştırmak isterseniz:

1.  **Bu depoyu klonlayın:**
    ```bash
    git clone https://github.com/stilkod/Miflon.git
    cd Miflon
    ```

2.  **Sanal bir ortam oluşturup aktif hale getirin (önerilir):**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Gerekli kütüphaneleri yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```
    *Not: Eğer `requirements.txt` dosyanız yoksa `pip freeze > requirements.txt` komutuyla oluşturabilirsiniz.*

4.  **Uygulamayı çalıştırın:**
    ```bash
    python miflon.py
    ```

## 🛠️ Teknoloji Yığını

*   **Dil:** Python 3
*   **Arayüz (GUI):** Tkinter
*   **Görüntü İşleme:** OpenCV (`opencv-python`)
*   **Görüntü Formatları ve Arayüz Uyumluluğu:** Pillow (PIL Fork)
*   **Paketleme:** PyInstaller

## 🤝 Katkıda Bulunma

Katkılarınız projeyi daha iyi bir hale getirecektir! Lütfen katkıda bulunmak için şu adımları izleyin:

1.  Bu depoyu **Fork**'layın.
2.  Yeni bir özellik dalı oluşturun (`git checkout -b ozellik/HarikaBirOzellik`).
3.  Değişikliklerinizi **Commit**'leyin (`git commit -m 'Yeni ve harika bir özellik eklendi'`).
4.  Dalınızı **Push**'layın (`git push origin ozellik/HarikaBirOzellik`).
5.  Bir **Pull Request** açın.

Hata bildirimleri veya özellik istekleri için lütfen [Issues](https://github.com/stilkod/Miflon/issues) bölümünü kullanın.

## 📝 Lisans

Bu proje, **MIT Lisansı** ile lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakınız.
