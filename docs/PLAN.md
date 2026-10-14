# Agentic Workflow Assistant — geliştirme planı

**Güncel yön:** Kullanıcının otomotiv odaklı demo talebi doğrultusunda genel refund/HR senaryoları yerine [İlan ve Trink Sat Operasyon Asistanı](VEHICLE-DEMO.md) geliştirildi. Bu belgedeki ilk aşama listesi başlangıç planıdır; güncel özellikler, doğrulamalar ve kalan işler VEHICLE-DEMO.md içinde tutulur.

Durum: Aşama 0 ve Aşama 1'in yerel uygulaması tamamlandı. Docker runtime doğrulaması, bu bilgisayarda Docker bulunmadığı için bekliyor. Sonraki uygulama adımı Aşama 2. Aşama 1 açıklaması: [MILESTONE-1.md](MILESTONE-1.md).

Projenin bütün kaynakları, çıktıları ve proje için oluşturulan geçici dosyalar `arabamcomicin` altında tutulacak. Başka projelerin dosyaları değiştirilmeyecek.

## 1. Ürün ve kapsam

Kullanıcı iş talebini yazar. Sistem niyeti belirler, ilgili şirket bilgisini bulur, gerekli araçlarla iş verisini sorgular ve kaynaklı bir cevap veya uygulanabilir aksiyon önerisi üretir. Hassas aksiyon insan onayı bekler. Uygulama sonrasında sonuç ve işlem geçmişi görünür olur.

Ana demo hikâyesi: ücretli bir ilan hizmeti için iade talebi. Kullanılan şirket, politika, sipariş ve kişiler tamamen kurgusal olacak; arabam.com'un gerçek kuralları temsil edilmeyecek.

İlk dikey akış iade olacak. HR, pazarlama ve destek akışları aynı sözleşmeleri ve servisleri kullanarak sırayla eklenecek.

MVP tek kullanıcı bağlamında, localhost üzerinde çalışan bir demo olacak. İstek sahibinin ve onaylayanın rolleri backend tarafından doğrulanan ayrı demo kimlikleriyle temsil edilecek. UI'daki bir role etiketi yetkilendirme yerine geçmeyecek. Kurumsal SSO, çok kiracılı kullanım ve gerçek ödeme entegrasyonu bu kapsamda bulunmayacak.

## 2. Mimari kararlar ve nedenleri

| Karar | Neden | Sınır / bedel |
| --- | --- | --- |
| Tek FastAPI uygulaması | Bir geliştirici bütün akışı izleyebilir; hata ayıklama ve yerel kurulum sade kalır. | Uzun işlemler için ileride ayrı worker gerekebilir. |
| PostgreSQL + pgvector | Talep, aksiyon, log ve belge vektörleri aynı veritabanında tutulur. | Küçük belge setinde önce exact similarity search; vektör indeksleri ölçüm gerektirdiğinde eklenir. |
| Küçük, açık bir workflow servisi | Niyet, retrieval, araç kullanımı ve onay adımları görünür olur. | Agent framework'ü eklemeden önce gerçek ihtiyaç aranır. |
| Pydantic sözleşmeleri | Model cevabı ve araç argümanları backend'de tip ve şema kontrolünden geçer. | Geçersiz sonuç bir kez düzelttirilebilir; devam ederse güvenli hata üretilir. |
| OpenAI/Anthropic adapter'ları | Workflow kodu sağlayıcının mesaj formatına bağımlı kalmaz. | Sağlayıcı farkları adapter içinde normalize edilir; iki sağlayıcı da ayrıca doğrulanır. |
| Ayrı embedding servisi | Metin üretimi ve vektör üretimi farklı sorumluluklardır. | Model/boyut değişince belge vektörleri yeniden oluşturulur. |
| Backend policy engine | Model önerir; izinleri ve iade koşullarını kod uygular. | Prompt içindeki bir talimat onay politikasını geçersiz kılamaz. |
| n8n sadece destek entegrasyonunda | Orkestrasyonun tamamını iki sistemde tekrar kurmadan gerçek bir entegrasyon gösterir. | Webhook kabulü işlem tamamlandı demek değildir; sonuç callback ile doğrulanır. |
| Kalıcı action state ve audit event | Yeniden başlatma, çift onay ve hata araştırması açıklanabilir hale gelir. | Audit log, iş durumunun yerine geçmez. |

Generation adapter: `generate_decision(context, tool_schemas) -> Decision`. Ortak araç çağrısı biçimi: `call_id`, `name`, `arguments`. Araç sonuçları tekrar model bağlamına verilir. En fazla üç read-tool turu ve sınırlı timeout/token bütçesi bulunur. Modelin üretim cevabıyla birlikte gizli düşünce zinciri istenmez; kullanıcıya açıklanabilir kısa karar özeti kaydedilir.

Embedding adapter: `embed(texts) -> vectors`. İlk canlı entegrasyonda tek bir embedding modeli kullanılır; Anthropic generation seçimi aynı retrieval altyapısıyla çalışır. Sağlayıcı değiştirmek embedding sağlayıcısını otomatik değiştirmez. Anahtarsız demo için açıkça etiketlenmiş deterministik fixture provider kullanılabilir; bu mod gerçek LLM/RAG kalite kanıtı sayılmaz.

## 3. Talep yaşam döngüsü

1. FastAPI talebi ve istek sahibini doğrular, bir `run` oluşturur.
2. Model niyeti belirler: `refund`, `hr`, `marketing`, `support`, `unknown`.
3. Eksik kritik bilgi varsa sistem açıklama ister; `unknown` niyet rastgele bir araç çalıştırmaz.
4. Belge seti bölüm/akışa göre filtrelenir; ilk aşamada küçük Markdown belgeleri, başlık bazlı parçalama ve top-k retrieval kullanılır.
5. Model gerekli read-tool çağrısını önerir. Backend izin verilen ad, argüman ve erişim bağlamını doğrular; sonucu modele verir.
6. Model yapılandırılmış cevap veya aksiyon önerisi üretir. Kaynak kimlikleri gerçekten alınan belge parçalarıyla karşılaştırılır.
7. Backend politika kontrolünü uygular. Uygunsuz iade önerisi bloke edilir; hassas aksiyon `pending_approval` olarak kalıcı kaydedilir.
8. Onaylayan, sabitlenmiş aksiyon payload'ını görür. Backend onun yetkisini ve aksiyonun hâlâ onay beklediğini doğrular.
9. Backend koşulları yeniden kontrol eder ve aynı payload'ı çalıştırır. Payload değişirse yeni onay gerekir; model bu aşamada yeniden aksiyon yazamaz.
10. Sonuç, araç olayları, latency ve varsa token kullanımı kaydedilir; UI güncel durumu gösterir.

Read tool örnekleri: `lookup_order`, `lookup_ticket`. Write tool örnekleri: `simulate_refund`, `save_campaign_brief`, `escalate_support`. HR cevapları aksiyon üretmez. Bütün write tool'lar ilk sürümde insan onayı ister; politika açıkça kodda tanımlanır.

Belge içeriği veri kabul edilir; belge içindeki 'kuralları yok say' türü ifadeler araç yetkisini değiştiremez. Kaynak yetersizse sistem kanıt varmış gibi cevap üretmek yerine açıklama ister veya bilgisinin yetersiz olduğunu belirtir.

### Yapılandırılmış çıktı örneği

```json
{
  "intent": "refund",
  "outcome": "propose_action",
  "answer": "Kurgusal iade politikasına göre talep uygun. İade işlemi onay bekliyor.",
  "decision_summary": "Sipariş bilgisi ve hizmet kullanım durumu kontrol edildi.",
  "citations": [{"chunk_id": "refund-policy:v1:2"}],
  "tool_calls": [],
  "proposed_action": {
    "tool": "simulate_refund",
    "arguments": {"order_id": "DEMO-1042"}
  }
}
```

Tutar ve para birimi sipariş kaydından backend tarafından hesaplanır; modelin yazdığı tutar işlem otoritesi değildir. `approval_required` model çıktısından değil backend politikasından üretilir. İade uygunluğu koşulları fixture policy ve servis kodunda aynı sürümle tutulur.

## 4. Veri modeli

UUID kimlikler, UTC timestamp'ler, ilişkiler için foreign key ve değişken payload'lar için JSONB kullanılacak. Para miktarları integer minor-unit olarak saklanacak; float kullanılmayacak.

| Tablo | Temel alanlar | Sorumluluk |
| --- | --- | --- |
| `documents` | id, title, source_path, department, version, content_hash, created_at | Kaynağın kimliği ve sürümü |
| `document_chunks` | id, document_id, ordinal, text, embedding, embedding_model, embedding_version | RAG parçaları; aynı embedding uzayındaki vektörler |
| `runs` | id, requester_id, request_text, intent, status, final_response_json, provider, model, prompt_version, started_at, finished_at | Talep ve nihai cevap |
| `run_events` | id, run_id, sequence, event_type, payload_json, created_at | Prompt, retrieval sonuçları, kısa karar, araç çağrısı/sonucu ve final response |
| `actions` | id, run_id, tool_name, arguments_json, payload_hash, status, idempotency_key, approved_by, approved_at, result_json, external_execution_id | Onaylanmış payload ve işlem durumu |
| `orders` | id, requester_id, amount_minor, currency, paid_at, service_used, refunded_at | Kurgusal siparişler ve iade kuralları |
| `support_tickets` | id, requester_id, subject, priority, status | Kurgusal destek kayıtları |
| `campaign_briefs` | id, action_id, title, brief_json, created_at | Onaylanmış pazarlama taslakları |
| `evaluation_results` | id, suite_id, case_id, run_id, checks_json, passed, latency_ms, created_at | Tekrarlanabilir değerlendirme sonuçları |

İlişkiler: document → chunks; run → events ve actions; evaluation_result → run; campaign_brief → action. `run_events(run_id, sequence)` ve `actions.idempotency_key` unique olacak. Sipariş başına çift iade backend ve transaction ile engellenecek.

Action durumları: `pending_approval → approved → executing → succeeded`; ayrıca `rejected`, `blocked`, `failed`, `outcome_unknown`. İkinci onay/çalıştırma isteği transaction ve conditional update ile aynı etkiyi tekrar oluşturamayacak. n8n'in sonucunun belirsiz olduğu timeout durumunda kör yeniden deneme yapılmayacak; durum uzlaştırılacak.

Run durumları: `received`, `processing`, `needs_information`, `answered`, `awaiting_approval`, `completed`, `rejected`, `failed`. `received`, talep kalıcı kaydedildiğinde fakat AI işlemesi başlamadığında kullanılır. Bir talep ilk sürümde en fazla bir write action üretecek.

Prompt logları sentetik demo verisiyle tutulacak, sırlar ve authorization header'ları kaydedilmeyecek. Tool event'leri argüman doğrulama ve sonuç özetini içerecek. Gerçek verili bir sürümde veri maskeleme, erişim ve saklama süresi ayrı olarak tasarlanmalı.

## 5. Planlanan klasör yapısı

Aşağıdaki ağaç hedef yapıdır. Aşama 1'de backend, frontend, migration, testler ve Compose eklendi. RAG/LLM, write tool, n8n ve eval dosyaları ilgili aşamada oluşturulacak. Docker olmayan bilgisayarlar için `tools/local-db` geliştirme yardımcısı eklendi.

```text
arabamcomicin/
  README.md
  .env.example
  .gitignore
  compose.yaml
  docs/
    PLAN.md
    DEMO.md
  backend/
    Dockerfile
    pyproject.toml
    app/
      main.py
      config.py
      db.py
      models.py
      schemas.py
      api/                 # runs, actions, callbacks
      services/            # workflow, retrieval, approval, audit
      llm/                 # base, openai, anthropic, fixture, embeddings
      tools/               # registry, orders, campaigns, support
      policies.py
    migrations/
    scripts/               # seed ve belge ingest
    tests/
  frontend/
    Dockerfile
    package.json
    src/
      App.tsx
      api.ts
      types.ts
      components/          # request form, sources, timeline, approval
  data/
    company_docs/          # sentetik Markdown belgeleri
    fixtures/              # sipariş, ticket ve demo kullanıcıları
  n8n/
    workflows/
      support-escalation.json
  evals/
    cases.jsonl
    run.py
    reports/
  .tmp/                    # proje içindeki geçici çıktılar, gitignore
```

## 6. API ve n8n sözleşmesi

- `POST /api/runs`: talep oluşturur; yanıt run kimliği ve durumdur.
- `GET /api/runs/{id}`: cevap, kaynaklar, olaylar ve aksiyon durumunu verir.
- `POST /api/actions/{id}/approve`: backend doğrulamalı onay ve kontrollü execution.
- `POST /api/actions/{id}/reject`: ret ve audit kaydı.
- `POST /api/integrations/n8n/result`: entegrasyon sırrıyla doğrulanmış sonuç callback'i.
- `GET /health`: servis durumu; ayrıca veritabanı readiness kontrolü.

n8n akışı: authenticated production webhook → payload doğrulama → aynı action ID ile backend result callback'i → response. Callback destek ticket'ını eskale duruma getirir ve audit event üretir; bu yerel operasyon kaydı entegrasyonun gözlemlenebilir sonucudur. Dış Slack/e-posta gönderimi gerekmez.

Test webhook'u geliştirmede kullanılabilir; Compose demo akışında import edilmiş ve aktive edilmiş production webhook'u kullanılacak. Backend → n8n ve n8n → backend adresleri Compose servis adlarıyla çözülecek. Callback yalnızca o action'ın beklenen execution kimliği ve mevcut durumuyla kabul edilecek; tekrarlanan callback aynı sonucu değiştirmeyecek. Hata ve belirsiz sonuç UI'da başarı olarak gösterilmeyecek.

## 7. Uygulama aşamaları ve kabul koşulları

Her aşamada: önce nedenini açıklama, küçük uygulama, ilgili kontrol/test, kısa demo ve öğrenme özeti. Bir sonraki aşamanın bütün kodu önceden üretilmeyecek.

| Aşama | Teslimat | Tamamlandığını nasıl anlayacağız? |
| --- | --- | --- |
| 0 — Tasarım | Mimari, veri modeli, klasör planı, kapsam | Bu belgeler mevcut; uygulama henüz yok |
| 1 — Temel iskelet | FastAPI, React, Postgres/pgvector, migration, Compose, sentetik seed | Yerelde health/readiness geçer; UI talep oluşturur ve DB'den kayıt okur |
| 2 — Kaynaklı HR cevabı | Belge ingest, embedding, retrieval, ilk canlı LLM adapter'ı, JSON doğrulama, audit | İzin sorusu gerçek ilgili kaynağa bağlanır; bilinmeyen politika uydurulmaz |
| 3 — İade dikey akışı | İkinci canlı LLM adapter'ı, read tool döngüsü, policy engine, onay ekranı, simüle write tool | Uygun talep onay öncesi iade oluşturmaz; onay sonrası bir kez uygulanır; ret ve uygun olmayan talep doğrulanır |
| 4 — Diğer iş akışları | Kampanya taslağı, destek eskalasyonu, çalışır n8n JSON | Onaylanan escalation n8n üzerinden ticket durumunu değiştirir; başarısız callback görünürdür |
| 5 — Ölçüm ve dayanıklılık | Eval CLI, hata senaryoları, timeout ve idempotency kontrolleri | Rapor üretir; injection ve çift işlem testleri geçer; her iki canlı adapter ayrıca çalıştırılır |
| 6 — Portföy sunumu | Son UI düzeni, doğrulanmış kurulum, diagram, screenshots, demo rehberi | Temiz yerel kurulumdan dört akış gösterilir; README gerçek ölçümleri ve sınırlamaları içerir |

Bir sonraki geliştirme adımı Aşama 2'dir. Aşama 1'de 12 backend testi, lint ve frontend build geçti; tarayıcıdan kayıt oluşturma ve yeniden açma doğrulandı. Bu doğrulama PostgreSQL/PGlite ile yapıldı; Docker build/runtime henüz doğrulanmadı. AI kalite ölçümleri sonraki aşamalara aittir.

## 8. Basit değerlendirme sistemi

Başlangıç hedefi dört akışa dengeli dağılmış 24 sentetik vaka. Her vaka: input, fixture bağlamı, beklenen intent, beklenen kaynak kimlikleri, beklenen tool, action eligibility ve approval koşulunu taşır. Metnin kelimesi kelimesine aynı olması beklenmez.

Deterministik ölçümler: intent doğruluğu, schema geçerliliği, retrieval recall@k, citation ID geçerliliği, beklenen tool seçimi, yanlış write action oranı, onay öncesi sıfır write execution ve çift işlem engeli. Retrieval için embedding modeli ve fixture sürümü raporda yer alır.

Cevap kalitesi: kaynakla tutarlılık, doğruluk ve işe yararlılık için 0–2 puanlık küçük bir insan değerlendirme rubriği. Geçerli citation ID tek başına cevap doğruluğu sayılmaz. İlk sürümde zorunlu LLM-as-judge eklenmez.

Özel vakalar: eksik sipariş ID, başkasının siparişi, uygun olmayan iade, az kaynak, belge içinde prompt injection, geçersiz JSON, bilinmeyen araç, sağlayıcı timeout'u, çift onay, payload değişimi, n8n hatası ve yinelenen callback. Güvenlik davranışı testleri ile LLM cevap kalitesi değerlendirmeleri ayrı raporlanır.

Fixture mode sistem sözleşmelerini test eder. Canlı mode gerçek provider ile çalışır; API anahtarı yoksa canlı test açıkça skipped olur, passed yazılmaz. Ölçümler provider, model, prompt ve belge sürümüyle kaydedilir.

İlk kabul hedefleri: deterministik güvenlik testlerinin tamamı geçmeli; diğer kalite oranları ölçülüp raporlanmalı ve iyileştirme için kullanılmalı. Demo verisinden gerçek şirkette zaman veya para kazancı sonucu çıkarılmayacak.

## 9. Mülakatta anlatılacak kararlar

1. İş problemi nasıl seçildi ve hangi başarı ölçütüne bağlandı?
2. RAG neden gerekli; hangi durumda kaynak yetersizliği bildiriliyor?
3. Modelin önerisi ile backend yetkisi nasıl ayrılıyor?
4. Onaydan sonra neden model yeniden aksiyon üretmiyor?
5. n8n timeout ve tekrar denemelerinde çift işlem nasıl önleniyor?
6. Provider değişince generation ve embedding neden ayrı ele alınıyor?
7. Başarılı örneklerin yanında hangi hata vakaları ölçüldü?

## 10. Teknik referanslar

- [pgvector: PostgreSQL içinde vektör saklama ve benzerlik arama](https://github.com/pgvector/pgvector)
- [n8n Webhook: test/production URL ve authentication](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)

Sağlayıcı SDK'ları ve sürümleri, ilgili adapter uygulanacağı aşamada resmi dokümantasyonla doğrulanacak.
