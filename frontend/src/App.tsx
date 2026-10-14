import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CarFront,
  Check,
  ChevronRight,
  CircleCheck,
  ClipboardCheck,
  Clock3,
  FileCheck2,
  FileSearch,
  Gauge,
  Image,
  Layers3,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Workflow,
  X,
} from "lucide-react";
import { api } from "./api";
import type {
  ReviewResult,
  ReviewTask,
  RunDetail,
  RunSummary,
  Vehicle,
} from "./types";
import "./domain.css";
import "./public-samples.css";

const money = (v: number | null) =>
  v === null
    ? "Belirtilmedi"
    : new Intl.NumberFormat("tr-TR").format(v) + " TL";
const time = (d: string) =>
  new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(d));
const statuses: Record<string, string> = {
  received: "Kaydedildi",
  awaiting_approval: "Onay bekliyor",
  completed: "Görev açıldı",
  answered: "Kontrol tamam",
  rejected: "Reddedildi",
  failed: "Tamamlanamadı",
};
const verdicts: Record<string, string> = {
  needs_review: "İnceleme gerekiyor",
  needs_information: "Bilgi tamamlanmalı",
  consistent: "Demo kontrolleri tutarlı",
};
const events: Record<string, string> = {
  request_received: "Talep alındı",
  prompt: "Model bağlamı hazırlandı",
  tool_call: "Okuma aracı seçildi",
  tool_result: "Araç kaydı sorgulandı",
  retrieval: "İlgili kurallar getirildi",
  action_proposed: "İnceleme görevi önerildi",
  final_response: "Kontrol sonucu kaydedildi",
  action_approved: "İnsan onayı alındı",
  action_rejected: "Öneri reddedildi",
  tool_executed: "Operasyon görevi açıldı",
  workflow_failed: "İş akışı durduruldu",
};
const angles: Record<string, string> = {
  front: "Ön",
  rear: "Arka",
  side: "Yan",
  interior: "İç",
  engine: "Motor",
};
const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "İşlem tamamlanamadı.";

function PublicPhotos({ vehicle }: { vehicle: Vehicle }) {
  const photos = vehicle.photos.filter((photo) => photo.url);
  const [index, setIndex] = useState(
    Math.min(3, Math.max(0, photos.length - 1)),
  );
  if (!photos.length)
    return <p className="metadata-note">İndirilen görsel bulunamadı.</p>;
  return (
    <div className="public-gallery">
      <img
        className="public-photo-main"
        src={photos[index].url}
        alt={vehicle.title + " · fotoğraf " + (index + 1)}
      />
      <div className="public-photo-strip">
        {photos.map((photo, position) => (
          <button
            key={photo.url}
            type="button"
            className={position === index ? "selected" : ""}
            onClick={() => setIndex(position)}
            aria-label={"Fotoğraf " + (position + 1)}
          >
            <img loading="lazy" src={photo.url} alt="" />
          </button>
        ))}
      </div>
      <p>
        {index + 1} / {photos.length} · {photos[index].width} ×{" "}
        {photos[index].height} · site önizlemesi
      </p>
    </div>
  );
}

function CarIllustration() {
  return (
    <svg
      viewBox="0 0 400 145"
      className="car-illustration"
      aria-label="Temsili araç çizimi"
      role="img"
    >
      <defs>
        <linearGradient id="car-body" x1="0" x2="1">
          <stop offset="0" stopColor="#becdd1" />
          <stop offset="1" stopColor="#e8f0ee" />
        </linearGradient>
      </defs>
      <ellipse cx="203" cy="123" rx="167" ry="9" fill="#cbd8d2" opacity=".35" />
      <path
        d="M38 91 63 82 91 46Q103 32 126 32H251Q269 32 283 47L324 77 356 83Q368 87 369 108L356 115H44L30 105Z"
        fill="url(#car-body)"
        stroke="#7c949b"
        strokeWidth="2"
      />
      <path
        d="m97 73 23-32h52v32zm85 0V41h66q12 0 23 13l21 19z"
        fill="#536e7b"
      />
      <path
        d="M58 88h20m244 0h29m-164-7h15m43 0h15M178 75v35m111-34 5 36"
        stroke="#8ca5ad"
        strokeWidth="2"
      />
      <path d="M30 99h34m275 0h31" stroke="#f3f9f6" strokeWidth="5" />
      <circle cx="94" cy="112" r="23" fill="#243a43" />
      <circle cx="94" cy="112" r="13" fill="#b3c4c9" />
      <circle cx="306" cy="112" r="23" fill="#243a43" />
      <circle cx="306" cy="112" r="13" fill="#b3c4c9" />
    </svg>
  );
}

export default function App() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [selectedId, setSelectedId] = useState("ILAN-1001");
  const [dataset, setDataset] = useState<"real" | "demo">("real");
  const [description, setDescription] = useState("");
  const [view, setView] = useState<"workspace" | "tasks" | "history">(
    "workspace",
  );
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [mode, setMode] = useState("fixture");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const selected = vehicles.find((item) => item.id === selectedId);
  const visibleVehicles = vehicles.filter((item) =>
    dataset === "real"
      ? item.id.startsWith("REAL-")
      : !item.id.startsWith("REAL-"),
  );
  const result = detail?.final_response_json as unknown as ReviewResult | null;
  const ready = result?.narrative ? result : null;
  const workflow = selectedId.startsWith("TRINK")
    ? "trink_readiness"
    : "listing_review";

  async function reload() {
    setLoading(true);
    setError("");
    try {
      await api.readiness();
      const [records, history, queue, meta] = await Promise.all([
        api.vehicles(),
        api.list(),
        api.tasks(),
        api.meta(),
      ]);
      setVehicles(records);
      // Shared review packages contain synthetic fixtures, not the private archive.
      // Open a useful default even when no public listing snapshots were imported.
      if (!records.some((record) => record.id.startsWith("REAL-"))) {
        setDataset("demo");
        setSelectedId((current) =>
          records.some((record) => record.id === current)
            ? current
            : records[0]?.id || "ILAN-1001",
        );
      }
      setRuns(history);
      setTasks(queue);
      setMode(meta.generation);
      setConnected(true);
    } catch (e) {
      setConnected(false);
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void reload();
  }, []);
  useEffect(() => {
    setDescription(selected?.description || "");
  }, [selected]);
  useEffect(() => {
    if (
      visibleVehicles.length &&
      !visibleVehicles.some((item) => item.id === selectedId)
    ) {
      setSelectedId(visibleVehicles[0].id);
      setDetail(null);
    }
  }, [vehicles, dataset, selectedId]);
  function choose(id: string) {
    setSelectedId(id);
    setDetail(null);
    setError("");
    setNotice("");
  }
  async function save() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const record = await api.updateDescription(selected.id, description);
      setVehicles((list) => list.map((v) => (v.id === record.id ? record : v)));
      setDetail(null);
      setNotice(
        "Açıklama yerel kayıtta güncellendi. Yeni haliyle tekrar kontrol edebilirsin.",
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function review() {
    if (!selected) return;
    setBusy(true);
    setError("");
    setNotice("");
    setDetail(null);
    try {
      const text =
        selected.id +
        (workflow === "listing_review"
          ? " ilanının beyan tutarlılığını, eksik bilgilerini ve fotoğraf kapsamını kontrol et. Gerekirse inceleme görevi öner."
          : " Trink Sat başvurusunun ekspertiz öncesi bilgi ve hazırlık eksiklerini kontrol et. Fiyat veya satın alma kararı verme.");
      const record = await api.review(selected.id, workflow, text);
      setDetail(record);
      setRuns((list) => [record, ...list].slice(0, 50));
      if (record.status === "failed")
        setError(
          String(record.final_response_json?.error || "Kontrol tamamlanamadı."),
        );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function decide(decision: "approve" | "reject") {
    if (!detail?.action) return;
    setBusy(true);
    setError("");
    try {
      await api.decide(detail.action.id, decision);
      const [record, queue] = await Promise.all([
        api.detail(detail.id),
        api.tasks(),
      ]);
      setDetail(record);
      setTasks(queue);
      setRuns((list) => list.map((r) => (r.id === record.id ? record : r)));
      setNotice(
        decision === "approve"
          ? "İnceleme görevi yerel kuyruğa eklendi. Satıcıya mesaj gönderilmedi."
          : "Öneri reddedildi; görev oluşturulmadı.",
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function open(id: string) {
    setBusy(true);
    setError("");
    try {
      const record = await api.detail(id);
      const listing = (
        record.final_response_json?.listing as Vehicle | undefined
      )?.id;
      if (listing) {
        setDataset(listing.startsWith("REAL-") ? "real" : "demo");
        setSelectedId(listing);
      }
      setDetail(record);
      setView("workspace");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell vehicle-app">
      <aside className="sidebar">
        <a href="#workspace" className="brand">
          <span className="brand-mark">
            <Workflow size={23} />
          </span>
          <span>
            agentic<span className="brand-dot">.</span>
            <small>VEHICLE OPERATIONS</small>
          </span>
        </a>
        <div className="workspace-tag">
          <span className="tiny-dot" /> Araç operasyonları <span>DEMO</span>
        </div>
        <p className="nav-label">ÇALIŞMA ALANI</p>
        <button
          className={"nav-item " + (view === "workspace" ? "active" : "")}
          onClick={() => setView("workspace")}
        >
          <FileSearch size={18} /> Kontrol merkezi <ChevronRight size={15} />
        </button>
        <button
          className={"nav-item " + (view === "tasks" ? "active" : "")}
          onClick={() => setView("tasks")}
        >
          <ClipboardCheck size={18} /> İnceleme kuyruğu{" "}
          <span className="queue-count">{tasks.length}</span>
        </button>
        <button
          className={"nav-item " + (view === "history" ? "active" : "")}
          onClick={() => setView("history")}
        >
          <Clock3 size={18} /> İşlem geçmişi
        </button>
        <div className="sidebar-note">
          <span className="note-icon">
            <Sparkles size={19} />
          </span>
          <strong>Bir kontrolün ötesinde.</strong>
          <p>
            Beyanı kontrol et.
            <br />
            Kaynağı göster. İşi ilerlet.
          </p>
          <span className="milestone-pill">BAĞIMSIZ PORTFÖY DEMOSU</span>
        </div>
        <div className="sidebar-footer">
          <span className="avatar">OP</span>
          <div>
            Operasyon çalışma alanı<small>Yerel demo · insan onayı</small>
          </div>
          <ShieldCheck size={16} />
        </div>
      </aside>
      <main id="workspace" className="main">
        <header className="topbar">
          <div className="breadcrumb">
            Araç operasyonları <ChevronRight size={14} />
            <span>
              {view === "workspace"
                ? "Kontrol merkezi"
                : view === "tasks"
                  ? "İnceleme kuyruğu"
                  : "İşlem geçmişi"}
            </span>
          </div>
          <div className={"connection " + (connected ? "online" : "")}>
            <span className="tiny-dot" />
            {loading
              ? "Bağlanıyor"
              : connected
                ? "Yerel servisler bağlı"
                : "Bağlantı yok"}
          </div>
        </header>
        <section className="page-heading">
          <p className="eyebrow">
            <span /> İLAN & TRINK SAT OPERASYON ASİSTANI
          </p>
          <h1>
            Eksik bilgiyi bul.
            <br className="mobile-break" /> Satış sürecini ilerlet.
          </h1>
          <p>
            Araç beyanlarını ve hazırlık bilgilerini kontrol eden, kaynak
            gösteren ve insan onayıyla işi ilerleten bir demo.
          </p>
        </section>
        <div className="domain-banner">
          <ShieldCheck size={19} />
          <div>
            <strong>
              {mode === "fixture"
                ? "Anahtarsız demo modu"
                : "Canlı model: " + mode}
            </strong>
            <p>
              {mode === "fixture"
                ? "Sonuçlar deterministik kurallarla üretilir; canlı LLM çalışmıyor."
                : "Canlı model açıklama üretir; aksiyon yetkisi backend kurallarıyla yönetilir."}{" "}
              {selected?.vehicle.source
                ? "Seçilen kayıt, indirilen gerçek ilanın yerel kopyasıdır. Fotoğraflardan hasar veya açı analizi yapılmıyor."
                : "Seçilen araç ve görsel bilgileri sentetik örnektir."}
            </p>
          </div>
          <span>YEREL DEMO</span>
        </div>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="notice visible" role="status">
            <Check size={16} />
            {notice}
          </div>
        )}
        {view === "workspace" && (
          <>
            <section className="scenario-section">
              <div className="section-heading">
                <h2>Bir örnek seç, iş akışını gör</h2>
                <span>
                  {visibleVehicles.length}{" "}
                  {dataset === "real"
                    ? "indirilen gerçek ilan"
                    : "demo senaryosu"}
                </span>
              </div>
              <div className="dataset-switch">
                <button
                  type="button"
                  disabled={busy}
                  className={dataset === "real" ? "active" : ""}
                  onClick={() => {
                    setDataset("real");
                    setDetail(null);
                  }}
                >
                  İndirilen gerçek ilanlar
                </button>
                <button
                  type="button"
                  disabled={busy}
                  className={dataset === "demo" ? "active" : ""}
                  onClick={() => {
                    setDataset("demo");
                    setDetail(null);
                  }}
                >
                  Kurgusal demo örnekleri
                </button>
              </div>
              <div className="scenario-grid">
                {visibleVehicles.map((item, index) => (
                  <button
                    key={item.id}
                    disabled={busy}
                    className={
                      "scenario-card " +
                      (selectedId === item.id ? "selected" : "")
                    }
                    onClick={() => choose(item.id)}
                  >
                    <span className="scenario-number">0{index + 1}</span>
                    <strong>{item.scenario}</strong>
                    <small>{item.title}</small>
                    <ChevronRight size={16} />
                  </button>
                ))}
              </div>
            </section>
            {selected ? (
              <div className="domain-grid">
                <section className="vehicle-column">
                  <div className="panel vehicle-record">
                    <div className="panel-title">
                      <CarFront size={18} />
                      <h2>Araç kaydı</h2>
                      <span className="small-label">{selected.id}</span>
                    </div>
                    {selected.vehicle.source ? (
                      <PublicPhotos key={selected.id} vehicle={selected} />
                    ) : (
                      <div className="vehicle-art">
                        <span>KURGUSAL ÖRNEK</span>
                        <CarIllustration />
                      </div>
                    )}
                    <div className="vehicle-body">
                      {selected.vehicle.source && (
                        <div className="public-provenance">
                          <strong>Gerçek ilan · yerel test kopyası</strong>
                          <span>
                            İndirme: {time(selected.vehicle.source.captured_at)}
                          </span>
                          <a
                            href={
                              "/api/samples/" +
                              selected.vehicle.source.listing_id +
                              "/offline"
                            }
                            target="_blank"
                            rel="noreferrer"
                          >
                            HTML kopyasını aç ↗
                          </a>
                          <a
                            href={selected.vehicle.source.url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Kaynak ilanı aç ↗
                          </a>
                        </div>
                      )}
                      <p className="vehicle-location">
                        {selected.vehicle.city} ·{" "}
                        {workflow === "trink_readiness"
                          ? "Trink Sat ön hazırlık"
                          : "İlan ön kontrol"}
                      </p>
                      <h2>{selected.title}</h2>
                      {selected.vehicle.advert_title && (
                        <p className="advert-headline">
                          <strong>İlan başlığı:</strong>{" "}
                          {selected.vehicle.advert_title}
                        </p>
                      )}
                      <div className="vehicle-specs">
                        <span>
                          <Gauge size={14} />{" "}
                          {selected.vehicle.km.toLocaleString("tr-TR")} km
                        </span>
                        <span>{selected.vehicle.gearbox}</span>
                        <span>{selected.vehicle.fuel}</span>
                      </div>
                      <dl className="vehicle-fields">
                        <div>
                          <dt>Boya beyanı</dt>
                          <dd>
                            {selected.vehicle.painted_parts === null
                              ? "Bilgi eksik"
                              : selected.vehicle.painted_parts.join(", ") ||
                                "Boya yok"}
                          </dd>
                        </div>
                        <div>
                          <dt>Hasar kaydı</dt>
                          <dd>{money(selected.vehicle.damage_record_try)}</dd>
                        </div>
                        <div>
                          <dt>
                            {workflow === "trink_readiness"
                              ? "Muayene süresi"
                              : "İstenen fiyat"}
                          </dt>
                          <dd>
                            {workflow === "trink_readiness"
                              ? (selected.vehicle.inspection_days_remaining ??
                                  "Bilinmiyor") + " gün"
                              : money(selected.vehicle.price_try)}
                          </dd>
                        </div>
                        <div>
                          <dt>
                            {selected.vehicle.source
                              ? "İndirilen fotoğraflar"
                              : "Görsel metadata’sı"}
                          </dt>
                          <dd>
                            {selected.photos.length}{" "}
                            {selected.vehicle.source
                              ? "gerçek fotoğraf"
                              : "örnek kayıt"}
                          </dd>
                        </div>
                      </dl>
                      <label
                        className="field-label"
                        htmlFor="listing-description"
                      >
                        Satıcı açıklaması <span>Düzenleyebilirsin</span>
                      </label>
                      <textarea
                        className="description-editor"
                        id="listing-description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        maxLength={4000}
                        disabled={busy}
                      />
                      <div className="description-actions">
                        {description !== selected.description ? (
                          <button
                            className="text-button"
                            disabled={busy || description.trim().length < 3}
                            onClick={() => void save()}
                          >
                            <Check size={14} /> Açıklamayı kaydet
                          </button>
                        ) : (
                          <span>Araç kaydı yerel veritabanından okundu.</span>
                        )}
                      </div>
                      {!selected.vehicle.source && (
                        <div className="photo-angles">
                          {Object.entries(angles).map(([angle, label]) => (
                            <span
                              key={angle}
                              className={
                                selected.photos.some((p) => p.angle === angle)
                                  ? "present"
                                  : ""
                              }
                            >
                              <Image size={13} />
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                      <p className="metadata-note">
                        {selected.vehicle.source
                          ? "Gerçek dosyaların boyutları okundu. Fotoğraf açıları sınıflandırılmadı; site önizleme boyutları orijinal fotoğraf kalitesi olarak yorumlanmaz."
                          : "Gerçek fotoğraf analizi yapılmaz; açı ve çözünürlük bilgisi örnek metadata’dan gelir."}
                      </p>
                      <button
                        className="review-button"
                        disabled={
                          busy ||
                          loading ||
                          description !== selected.description
                        }
                        onClick={() => void review()}
                      >
                        {busy ? (
                          <LoaderCircle size={17} className="spin" />
                        ) : (
                          <Sparkles size={17} />
                        )}{" "}
                        {busy
                          ? "İş akışı çalışıyor…"
                          : workflow === "trink_readiness"
                            ? "Ön hazırlığı kontrol et"
                            : "İlanı kontrol et"}
                        <ArrowRight size={17} />
                      </button>
                    </div>
                  </div>
                </section>
                <section className="panel review-panel">
                  <div className="panel-title">
                    <FileCheck2 size={18} />
                    <h2>Kontrol ve bir sonraki adım</h2>
                    {detail && (
                      <span className="small-label">
                        {statuses[detail.status] || detail.status}
                      </span>
                    )}
                  </div>
                  {busy && !detail ? (
                    <div className="review-empty">
                      <LoaderCircle size={34} className="spin" />
                      <h3>Kayıt ve ilgili kurallar inceleniyor</h3>
                      <p>Sonuç, kaynaklar ve işlem geçmişi burada görünecek.</p>
                    </div>
                  ) : ready ? (
                    <div className="review-content">
                      <div
                        className={
                          "verdict " +
                          (ready.verdict === "consistent"
                            ? "good"
                            : "attention")
                        }
                      >
                        {ready.verdict === "consistent" ? (
                          <CircleCheck size={22} />
                        ) : (
                          <AlertTriangle size={22} />
                        )}
                        <div>
                          <strong>{verdicts[ready.verdict]}</strong>
                          <span>
                            {ready.findings.length} kontrol başlığı ·{" "}
                            {ready.sources.length} kaynak · {ready.latency_ms}{" "}
                            ms
                          </span>
                        </div>
                      </div>
                      <p className="review-summary">
                        {ready.narrative.summary}
                      </p>
                      <div className="finding-list">
                        {ready.findings.map((f) => (
                          <article className="finding" key={f.code}>
                            <span className={"finding-dot " + f.severity} />
                            <div>
                              <h3>{f.title}</h3>
                              <p>{f.detail}</p>
                              <span className="finding-source">
                                <BookOpen size={11} />
                                {ready.sources.find((s) => s.id === f.source_id)
                                  ?.title || f.source_id}
                              </span>
                            </div>
                          </article>
                        ))}
                      </div>
                      <div className="message-draft">
                        <div>
                          <MessageSquareText size={16} />
                          <strong>Satıcıya sorulacak mesaj</strong>
                          <span>TASLAK</span>
                        </div>
                        <p>{ready.narrative.seller_message}</p>
                        <small>
                          Gönderilmedi. Yalnızca inceleme görevinin içeriğine
                          eklenecek.
                        </small>
                      </div>
                      {detail?.action && (
                        <div className="approval-box">
                          <div>
                            <ShieldCheck size={18} />
                            <strong>
                              {detail.action.status === "pending_approval"
                                ? "İnceleme görevi için insan onayı"
                                : detail.action.status === "succeeded"
                                  ? "İnceleme görevi oluşturuldu"
                                  : "İnceleme önerisi reddedildi"}
                            </strong>
                          </div>
                          <p>
                            {detail.action.status === "pending_approval"
                              ? "Demo inceleyici olarak onay verirsen bulgular ve mesaj taslağı yerel operasyon kuyruğuna kaydedilecek."
                              : detail.action.status === "succeeded"
                                ? "Sonucu İnceleme kuyruğu sekmesinde görebilirsin. İlan yayımlanmadı, mesaj gönderilmedi."
                                : "Herhangi bir görev veya dış işlem oluşturulmadı."}
                          </p>
                          {detail.action.status === "pending_approval" && (
                            <div className="approval-buttons">
                              <button
                                disabled={busy}
                                onClick={() => void decide("reject")}
                              >
                                <X size={14} /> Reddet
                              </button>
                              <button
                                className="approve-button"
                                disabled={busy}
                                onClick={() => void decide("approve")}
                              >
                                <Check size={15} /> Onayla ve görev aç
                              </button>
                            </div>
                          )}
                          {Boolean(detail.action.result_json?.task_id) && (
                            <small>
                              GÖREV /{" "}
                              {String(detail.action.result_json?.task_id).slice(
                                0,
                                8,
                              )}
                            </small>
                          )}
                        </div>
                      )}
                      <div className="source-list">
                        <h3>
                          <BookOpen size={15} /> Kullanılan kaynaklar
                        </h3>
                        {ready.sources.map((s) => (
                          <details key={s.id}>
                            <summary>
                              {s.title}
                              <span>
                                {s.kind === "synthetic_policy"
                                  ? "DEMO KURALI"
                                  : "KAMUSAL ÖZET"}
                              </span>
                            </summary>
                            <p>{s.body}</p>
                            {s.url && (
                              <a href={s.url} target="_blank" rel="noreferrer">
                                Orijinal kaynağı aç ↗
                              </a>
                            )}
                            <small>Sürüm: {s.version}</small>
                          </details>
                        ))}
                      </div>
                      <details className="audit-details">
                        <summary>
                          <Workflow size={15} /> İşlem geçmişi ·{" "}
                          {detail?.events.length} kayıt
                        </summary>
                        <ol>
                          {detail?.events.map((e) => (
                            <li key={e.sequence}>
                              <strong>
                                {events[e.event_type] || e.event_type}
                              </strong>
                              <small>{time(e.created_at)}</small>
                              <details>
                                <summary>Teknik kaydı göster</summary>
                                <pre>
                                  {JSON.stringify(e.payload_json, null, 2)}
                                </pre>
                              </details>
                            </li>
                          ))}
                        </ol>
                      </details>
                    </div>
                  ) : (
                    <div className="review-empty">
                      <span className="empty-review-icon">
                        <FileSearch size={34} />
                      </span>
                      <h3>Bir araç kaydı, somut bir iş akışı.</h3>
                      <p>
                        Soldaki örneği kontrol et.
                        <br />
                        Bulguları gör, kaynakları incele
                        <br />
                        ve gerekiyorsa görevi onayla.
                      </p>
                      <div className="review-steps">
                        <span>01 · Kaydı oku</span>
                        <span>02 · Kuralla karşılaştır</span>
                        <span>03 · Onayla ve ilerlet</span>
                      </div>
                    </div>
                  )}
                  <div className="detail-footer">
                    <ShieldCheck size={14} /> Kontrol sonucu, gerçek ekspertiz
                    veya yayın onayı değildir.
                  </div>
                </section>
              </div>
            ) : (
              <div className="panel empty-state">
                <CarFront size={30} />
                <p>
                  {loading
                    ? "Örnek kayıtlar yükleniyor…"
                    : "Örnek kayıtlar bulunamadı. Backend seed adımını kontrol edin."}
                </p>
                <button className="text-button" onClick={() => void reload()}>
                  <RefreshCw size={14} /> Yeniden dene
                </button>
              </div>
            )}
          </>
        )}
        {view === "tasks" && (
          <section className="panel domain-table">
            <div className="panel-title">
              <ClipboardCheck size={18} />
              <h2>Onaylanmış inceleme görevleri</h2>
              <button
                className="icon-button"
                onClick={() => void reload()}
                aria-label="Kuyruğu yenile"
              >
                <RefreshCw size={16} />
              </button>
            </div>
            <p className="table-note">
              Yalnızca onay verilen aksiyonlar burada kayıt oluşturur. Gerçek
              ilan yayını veya mesaj gönderimi içermez.
            </p>
            {tasks.length ? (
              tasks.map((t) => (
                <div className="task-row" key={t.id}>
                  <span className="task-icon">
                    <ClipboardCheck size={19} />
                  </span>
                  <div>
                    <strong>{t.listing_id} · Araç bilgisi inceleme</strong>
                    <small>
                      {time(t.created_at)} · Görev {t.id.slice(0, 8)}
                    </small>
                  </div>
                  <span className="status-badge">Açık görev</span>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <ClipboardCheck size={30} />
                <h3>Henüz onaylanmış görev yok</h3>
                <p>
                  Kontrol merkezinde bir öneriyi onaylayınca burada görünür.
                </p>
              </div>
            )}
          </section>
        )}
        {view === "history" && (
          <section className="panel domain-table">
            <div className="panel-title">
              <Layers3 size={18} />
              <h2>Kalıcı işlem geçmişi</h2>
              <button
                className="icon-button"
                onClick={() => void reload()}
                aria-label="Geçmişi yenile"
              >
                <RefreshCw size={16} />
              </button>
            </div>
            {runs.length ? (
              runs.map((r) => (
                <button
                  disabled={busy}
                  className="history-row"
                  key={r.id}
                  onClick={() => void open(r.id)}
                >
                  <Clock3 size={17} />
                  <div>
                    <strong>{r.request_text}</strong>
                    <small>
                      {time(r.started_at)} · {r.id.slice(0, 8)}
                    </small>
                  </div>
                  <span className="status-badge">
                    {statuses[r.status] || r.status}
                  </span>
                  <ChevronRight size={16} />
                </button>
              ))
            ) : (
              <div className="empty-state">Henüz işlem yapılmadı.</div>
            )}
          </section>
        )}
        <footer className="page-footer">
          <span>Agentic Workflow Assistant · Bağımsız portföy projesi</span>
          <span>Bağımsız demo · Kurgusal örnekler ve yerel ilan kopyaları</span>
        </footer>
      </main>
    </div>
  );
}
