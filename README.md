<div align="center">

# ForceGraph

Yapay zekâ destekli kodlama araçlarına, proje hakkında daha az ve daha doğru
bağlam veren yerel bir yardımcı.

[Kurulum](#kurulum) · [Nasıl çalışır?](#nasıl-çalışır) · [Çoklu ajan kullanımı](#çoklu-ajan-kullanımı) · [English](#english)

</div>

## ForceGraph nedir?

Bir kodlama aracı projeyi anlamaya çalışırken çok sayıda dosya okuyabilir. Aynı
projede birkaç yapay zekâ süreci çalışıyorsa her biri benzer araştırmaları
tekrarlayabilir.

ForceGraph projeyi bir kod grafına dönüştürür. Fonksiyonlar, sınıflar, çağrılar,
bağımlılıklar ve testler arasındaki ilişkileri yerel bir SQLite veritabanında
tutar. Kodlama aracı bütün projeyi yeniden okumak yerine yaptığı işle ilgili
küçük bir bölüm ister.

ForceGraph ayrıca aynı proje üzerinde çalışan süreçlerin kısa notlar
paylaşmasını sağlar. Böylece bir sürecin bulduğu bilgiyi diğeri baştan aramak
zorunda kalmaz.

Bu belgede “ajan” sözcüğü, proje üzerinde çalışan bir yapay zekâ sürecini ifade
eder.

## Kurulum

Proje klasöründe şu komutu bir kez çalıştırın:

```bash
uvx --from "git+https://github.com/samansarmasik-alt/code-review-graph.git" forcegraph connect
```

Komut şunları yapar:

1. Bilgisayarda bulunan destekli kodlama araçlarını belirler.
2. Var olan MCP ayarlarını silmeden ForceGraph bağlantısını ekler.
3. Projenin kod grafını oluşturur.
4. Dosya değişikliklerinin otomatik izlenmesini açar.
5. Kurulum sonucunu `.code-review-graph/quickstart-receipt.json` dosyasına yazar.
6. Tanınmayan MCP istemcileri için `.code-review-graph/mcp-config.json` üretir.

Kurulumdan sonra kodlama aracını bir kez yeniden başlatmak gerekebilir.

`uvx` kullanılamıyorsa:

```bash
python -m pip install "git+https://github.com/samansarmasik-alt/code-review-graph.git"
forcegraph connect
```

Kurulumu başka bir kodlama aracına yaptırmak için şu isteği verebilirsiniz:

> Bu projeye ForceGraph’ı bağla:
> https://github.com/samansarmasik-alt/code-review-graph  
> AI_INSTALL.md içindeki adımları uygula. Doğrulama kaydı hazır olmadan işlemi
> tamamlanmış sayma.

## Nasıl çalışır?

Kullanıcı normal bir istek yazar. ForceGraph isteğin türünü Türkçe veya İngilizce
metinden belirler ve uygun graf sorgusunu seçer.

| Kullanıcının isteği | ForceGraph’ın hazırladığı bilgi |
| --- | --- |
| “Bu proje ne yapıyor?” | Kısa mimari görünüm |
| “Giriş hatasını bul” | İlgili fonksiyonlar ve bağlantılar |
| “Bu değişiklik nereyi etkiler?” | Bağımlılar ve etki alanı |
| “Bu fonksiyonu kim çağırıyor?” | Çağıranlar ve ilgili testler |
| “Değişiklikleri incele” | Değişiklik, risk ve test bilgisi |

Kullanıcının graf komutlarını veya MCP araç adlarını bilmesi gerekmez.

## Neden beş araç gösteriliyor?

Projenin gelişmiş kullanım için çok sayıda analiz aracı vardır. Bunların tümünü
her konuşmada modele göstermek gereksiz bağlam tüketebilir.

Standart bağlantıda yalnızca şu beş araç görünür:

| Araç | Görevi |
| --- | --- |
| `forcegraph_context_tool` | İsteğe uygun kod bağlamını hazırlar |
| `forcegraph_memory_tool` | Ajanlar arasında not ve devir bilgisi paylaşır |
| `forcegraph_passport_tool` | Ortak görevin durumunu ve sonraki adımını tutar |
| `detect_changes_tool` | Değişiklikleri ve riskleri ayrıntılı inceler |
| `build_or_update_graph_tool` | Kod grafını oluşturur veya yeniler |

Diğer araçlar kaldırılmaz. Gerektiğinde tam araç listesi açılabilir:

```bash
forcegraph serve --tool-profile full
```

## Çoklu ajan kullanımı

Aynı proje ve aynı Git dalı üzerinde çalışan ajanlar ortak görev kaydını
kendiliğinden kullanır. Normal kullanımda `task_id` veya `agent_id` yazmak
gerekmez.

Ortak görev kaydında şu bilgiler bulunur:

1. Görevin amacı
2. Görevin güncel durumu
3. Görevi üstlenen ajan
4. Kısa çalışma özeti
5. Sıradaki işlem

Örnek:

```json
{
  "goal": "Giriş zaman aşımı sorununu düzelt",
  "status": "in_progress",
  "owner_agent": "worker-2",
  "summary": "Sorun Redis zaman aşımı yoluna kadar daraltıldı",
  "next_action": "Zaman aşımı testini ekle"
}
```

Ajanlar ayrıca karar, bulgu, not ve devir bilgisi bırakabilir. Bütün konuşma
geçmişi saklanmaz. Amaç, tekrar edilen araştırmayı azaltırken yeni ve büyük bir
konuşma geçmişi oluşturmamaktır.

Görev kimliği şu sırayla belirlenir:

1. Açıkça verilen görev kimliği
2. `FORCEGRAPH_TASK_ID` ortam değişkeni
3. Kullanılan Git dalı
4. Git yoksa çalışma alanı

Ortak hafıza `.code-review-graph/agent-memory.db` dosyasında tutulur. Aynı
dosyaya erişebilen ayrı terminal süreçleri birlikte çalışabilir.

Farklı makinelerde veya birbirinden tamamen ayrılmış çalışma alanlarında yerel
hafıza kendiliğinden paylaşılmaz.

## Sınırlar nasıl uygulanır?

ForceGraph büyük bir notu sırf uzun olduğu için reddetmez. Notun tamamı yerel
veritabanında kalır. Modele gönderilen bölüm ise kullanılabilir bağlama göre
küçültülür.

İstenen bağlam miktarı alışılmadık bir değer olsa bile işlem durdurulmaz.
ForceGraph sonuç sayısını ve graf derinliğini uygun bir değere çevirir.

Ortak hafıza veya görev kaydı geçici olarak açılamazsa kod bağlamı yine döner.
Bu durumda yalnızca ortak çalışma özelliğinin kullanılamadığı bildirilir.

Hafıza kayıtlarında sık görülen parola, erişim anahtarı ve belirteç biçimleri
diske yazılmadan önce gizlenir. Bu koruma yararlıdır ancak eksiksiz bir gizli
bilgi tarayıcısının yerini tutmaz.

## Orijinal projeden farkı nedir?

ForceGraph,
[`tirth8205/code-review-graph`](https://github.com/tirth8205/code-review-graph)
projesinin MIT lisanslı geliştirme dalıdır. Kod grafı motoru ve temel analiz
özellikleri bu projeden gelir.

ForceGraph’ın eklediği bölüm, bu motorun farklı kodlama araçlarında daha az
ayar gerektirerek kullanılmasına odaklanır.

| Konu | Orijinal proje | ForceGraph |
| --- | --- | --- |
| Yerel kod grafı | Var | Var |
| Gelişmiş graf araçları | Doğrudan kullanılabilir | Tam görünümde kullanılabilir |
| Otomatik araç belirleme | Kurulum seçenekleri var | `connect` içinde yapılır |
| Türkçe istek sınıflandırması | Temel görev bağlamı var | Türkçe ve İngilizce yönlendirme var |
| Standart MCP görünümü | Geniş araç listesi | Beş araç |
| Çoklu ajan ortak hafızası | Temel özellik değil | Yerel olarak var |
| Ortak görev kaydı | Temel özellik değil | Amaç, sahip, durum ve sonraki işlem tutulur |
| Kurulum doğrulaması | Durum komutları var | Makine tarafından okunabilen kayıt üretilir |

Gelişmiş graf araçlarını tek tek yönetmek isteyenler için orijinal proje daha
doğrudan olabilir. Bir kodlama aracına projeyi bağlayıp uygun bağlamı kendisinin
seçmesini isteyenler için ForceGraph daha kolay bir kullanım sunar.

## Token kullanımı hakkında

Orijinal motorun yayımlanmış ölçümlerinde, bütün kaynak kodu okuma
karşılaştırmasına göre soru başına graf bağlamı medyan olarak yaklaşık 82 kat
daha küçüktür. Ölçüm yöntemi
[`docs/REPRODUCING.md`](docs/REPRODUCING.md) içinde açıklanır.

Bu sayı toplam konuşma maliyetinin 82 kat azalacağı anlamına gelmez. Sistem
talimatları, konuşma geçmişi, modelin işlemesi ve üretilen cevap ayrı token
kullanır.

ForceGraph şu tekrarları azaltmayı amaçlar:

1. Aynı proje dosyalarının yeniden okunması
2. Kullanılmayan MCP araçlarının modele tanıtılması
3. Farklı ajanların aynı araştırmayı yeniden yapması

Beş araçlık görünüm ve ortak görev kaydı için ayrıca bağımsız bir model ölçümü
henüz yayımlanmadı. Ölçülmemiş bir kazanç için kesin oran verilmez.

## Ne zaman kullanmaya değmez?

ForceGraph her proje için gerekli değildir.

Şu durumlarda kazanç az olabilir:

1. Proje yalnızca birkaç küçük dosyadan oluşuyorsa
2. Yapılacak iş tek bir dosyada açıkça belliyse
3. Kullanılan kodlama aracı MCP veya terminal komutu desteklemiyorsa
4. Farklı makineler arasında bulut tabanlı ortak hafıza gerekiyorsa

## Desteklenen araçlar

Codex, Claude Code, Cursor, Windsurf, Zed, Continue, OpenCode, Gemini CLI,
Qwen Code, Qoder, Kiro, GitHub Copilot ve CodeBuddy için kurulum desteği vardır.

## Yerel dosyalar

ForceGraph çalışma verilerini `.code-review-graph` klasöründe tutar:

| Dosya | İçeriği |
| --- | --- |
| `graph.db` | Kod grafı |
| `agent-memory.db` | Ajan notları ve ortak görev kayıtları |
| `mcp-config.json` | Genel MCP bağlantı ayarı |
| `quickstart-receipt.json` | Kurulum doğrulama sonucu |

Bu klasör kaynak denetimine eklenmez.

## Belgeler

| Belge | Konu |
| --- | --- |
| [AI_INSTALL.md](AI_INSTALL.md) | Bir kodlama aracının uygulayacağı kurulum adımları |
| [Entegrasyonlar](docs/INTEGRATIONS.md) | Desteklenen istemciler |
| [Kullanım](docs/USAGE.md) | Ayrıntılı kullanım |
| [Komutlar](docs/COMMANDS.md) | Komut ve araç başvurusu |
| [Mimari](docs/architecture.md) | İç yapı |
| [Yol haritası](docs/FORCEGRAPH_ROADMAP.md) | Planlanan geliştirmeler |
| [Atıf](ATTRIBUTION.md) | Kaynak proje ve lisans bilgisi |

## English

ForceGraph is a local code context layer for AI coding tools. It builds on the
MIT licensed `tirth8205/code-review-graph` engine and adds automatic client
setup, Turkish and English task routing, a smaller MCP tool surface, shared
local memory, and a compact task record for parallel agents.

Install it once from the repository root:

```bash
uvx --from "git+https://github.com/samansarmasik-alt/code-review-graph.git" forcegraph connect
```

Source code, graph data, shared notes, and task records remain local. See
[AI installation](AI_INSTALL.md), [integrations](docs/INTEGRATIONS.md),
[usage](docs/USAGE.md), and [attribution](ATTRIBUTION.md).

## License

[MIT](LICENSE)
