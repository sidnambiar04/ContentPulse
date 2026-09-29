import { useEffect, useState, useMemo } from "react";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowUpDown,
  CheckCircle,
  Clock,
  ExternalLink,
  Eye,
  FileText,
  Filter,
  Globe,
  Layers,
  Play,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Trash2,
  X,
  XCircle,
  Zap,
  Edit3,
  Info,
} from "lucide-react";

import {
  getDashboardStats,
  getCompetitors,
  getCompetitorDetail,
  getArticles,
  getMonitoringLogs,
  updateCompetitor,
  updateCompetitorDetails,
  createCompetitor,
  deleteCompetitor,
  checkCompetitorNow,
  checkAllNow,
} from "./api";

import "./App.css";

function App() {
  // ==========================================================
  // CORE STATE
  // ==========================================================
  const [stats, setStats] = useState(null);
  const [competitors, setCompetitors] = useState([]);
  const [articles, setArticles] = useState([]);
  const [logs, setLogs] = useState([]);

  const [activePage, setActivePage] = useState("dashboard");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);

  // ==========================================================
  // MODALS STATE
  // ==========================================================
  const [showAddCompetitor, setShowAddCompetitor] = useState(false);
  const [newCompetitor, setNewCompetitor] = useState({
    name: "",
    website_url: "",
    blog_url: "",
    check_interval_minutes: 1,
  });
  const [addingCompetitor, setAddingCompetitor] = useState(false);

  // Edit Competitor Modal
  const [editingCompetitor, setEditingCompetitor] = useState(null);
  const [savingEdit, setSavingEdit] = useState(false);

  // Competitor Details Modal
  const [selectedCompetitor, setSelectedCompetitor] = useState(null);
  const [competitorDetailData, setCompetitorDetailData] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Article Details Modal
  const [selectedArticle, setSelectedArticle] = useState(null);

  // Delete Confirmation Modal
  const [deletingCompetitor, setDeletingCompetitor] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Manual Check Loading
  const [checkingCompetitorId, setCheckingCompetitorId] = useState(null);
  const [checkingAll, setCheckingAll] = useState(false);

  // ==========================================================
  // ARTICLE PAGE FILTERS & SORT
  // ==========================================================
  const [articleSearch, setArticleSearch] = useState("");
  const [articleCompFilter, setArticleCompFilter] = useState("all");
  const [articleMethodFilter, setArticleMethodFilter] = useState("all");
  const [articleSort, setArticleSort] = useState("newest_detected");

  // ==========================================================
  // MONITORING PAGE FILTERS
  // ==========================================================
  const [logCompFilter, setLogCompFilter] = useState("all");
  const [logStatusFilter, setLogStatusFilter] = useState("all");

  // Competitor Search
  const [compSearch, setCompSearch] = useState("");

  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 5000);
  };

  // ==========================================================
  // DATA LOADER
  // ==========================================================
  const loadDashboard = async () => {
    try {
      setError(null);
      const [statsData, competitorsData, articlesData, logsData] =
        await Promise.all([
          getDashboardStats(),
          getCompetitors(),
          getArticles(),
          getMonitoringLogs(),
        ]);

      setStats(statsData);
      setCompetitors(competitorsData);
      setArticles(articlesData);
      setLogs(logsData);
    } catch (err) {
      console.error(err);
      setError("Unable to connect to the ContentPulse backend API.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboard();
  };

  // ==========================================================
  // COMPETITOR ACTIONS
  // ==========================================================
  const handleToggle = async (competitorId, currentStatus) => {
    try {
      setError(null);
      await updateCompetitor(competitorId, !currentStatus);
      showToast(
        `Monitoring ${!currentStatus ? "enabled" : "disabled"} for competitor.`
      );
      await loadDashboard();
    } catch (err) {
      console.error(err);
      setError("Failed to update competitor monitoring status.");
    }
  };

  const handleAddCompetitor = async (event) => {
    event.preventDefault();
    if (!newCompetitor.name.trim()) {
      setError("Competitor name is required.");
      return;
    }
    if (!newCompetitor.website_url.trim()) {
      setError("Website URL is required.");
      return;
    }

    try {
      setAddingCompetitor(true);
      setError(null);

      await createCompetitor({
        name: newCompetitor.name.trim(),
        website_url: newCompetitor.website_url.trim(),
        blog_url: newCompetitor.blog_url.trim() || null,
        check_interval_minutes: Number(newCompetitor.check_interval_minutes) || 1,
      });

      setNewCompetitor({ name: "", website_url: "", blog_url: "", check_interval_minutes: 1 });
      setShowAddCompetitor(false);
      showToast("Competitor added! Running first scan in the background…");
      await loadDashboard();
      setActivePage("competitors");
      // Auto-refresh after 8s so the background initial check results appear
      setTimeout(() => loadDashboard(), 8000);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Failed to add competitor.");
    } finally {
      setAddingCompetitor(false);
    }
  };

  const handleSaveEditCompetitor = async (event) => {
    event.preventDefault();
    if (!editingCompetitor) return;

    try {
      setSavingEdit(true);
      setError(null);
      await updateCompetitorDetails(editingCompetitor.id, {
        name: editingCompetitor.name,
        website_url: editingCompetitor.website_url,
        blog_url: editingCompetitor.blog_url || null,
        rss_url: editingCompetitor.rss_url || null,
        sitemap_url: editingCompetitor.sitemap_url || null,
        monitoring_enabled: editingCompetitor.monitoring_enabled,
        check_interval_minutes: editingCompetitor.check_interval_minutes || 1,
      });

      setEditingCompetitor(null);
      showToast("Competitor updated successfully.");
      await loadDashboard();
    } catch (err) {
      console.error(err);
      setError("Failed to update competitor.");
    } finally {
      setSavingEdit(false);
    }
  };

  const handleConfirmDeleteCompetitor = async () => {
    if (!deletingCompetitor) return;
    try {
      setIsDeleting(true);
      setError(null);
      await deleteCompetitor(deletingCompetitor.id);
      setDeletingCompetitor(null);
      showToast("Competitor and related data deleted successfully.");
      await loadDashboard();
    } catch (err) {
      console.error(err);
      const msg = err?.response?.data?.detail || err?.response?.data?.error || "Failed to delete competitor.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCheckNow = async (competitorId, competitorName) => {
    try {
      setCheckingCompetitorId(competitorId);
      setError(null);
      const res = await checkCompetitorNow(competitorId);
      const newArticles = res.new_articles ?? 0;
      showToast(
        `Check complete for ${competitorName || "Competitor"}: ${newArticles} new article(s) found.`,
        res.success ? "success" : "info"
      );
      await loadDashboard();
    } catch (err) {
      console.error(err);
      showToast(
        `Check failed for ${competitorName || "Competitor"}: ${err.message}`,
        "error"
      );
    } finally {
      setCheckingCompetitorId(null);
    }
  };

  const handleCheckAllNow = async () => {
    try {
      setCheckingAll(true);
      setError(null);
      const res = await checkAllNow();
      showToast(
        `⚡ Scan started for ${res.total} competitors — refreshing in 15 seconds…`,
        "info"
      );
      // Auto-refresh after 15s to pick up results from the background scan
      setTimeout(async () => {
        await loadDashboard();
        setCheckingAll(false);
        showToast("Dashboard refreshed with latest scan results.", "success");
      }, 15000);
    } catch (err) {
      console.error(err);
      setCheckingAll(false);
      showToast("Scan All failed — backend may be starting up. Try again in 30s.", "error");
    }
  };

  const handleOpenCompetitorDetail = async (competitor) => {
    setSelectedCompetitor(competitor);
    setLoadingDetail(true);
    try {
      const data = await getCompetitorDetail(competitor.id);
      setCompetitorDetailData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // ==========================================================
  // FILTERED ARTICLES
  // ==========================================================
  const filteredArticles = useMemo(() => {
    return articles
      .filter((article) => {
        // Search
        if (articleSearch.trim()) {
          const q = articleSearch.toLowerCase();
          const matchTitle = (article.title || "").toLowerCase().includes(q);
          const matchAuthor = (article.author || "").toLowerCase().includes(q);
          const matchComp = (article.competitor_name || "").toLowerCase().includes(q);
          const matchUrl = (article.url || "").toLowerCase().includes(q);
          if (!matchTitle && !matchAuthor && !matchComp && !matchUrl) {
            return false;
          }
        }
        // Competitor filter
        if (
          articleCompFilter !== "all" &&
          String(article.competitor_id) !== String(articleCompFilter)
        ) {
          return false;
        }
        // Method filter
        if (
          articleMethodFilter !== "all" &&
          (article.detection_method || "").toLowerCase() !==
            articleMethodFilter.toLowerCase()
        ) {
          return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (articleSort === "newest_detected") {
          return new Date(b.detected_at || 0) - new Date(a.detected_at || 0);
        }
        if (articleSort === "oldest_detected") {
          return new Date(a.detected_at || 0) - new Date(b.detected_at || 0);
        }
        if (articleSort === "newest_published") {
          return new Date(b.published_at || 0) - new Date(a.published_at || 0);
        }
        if (articleSort === "fastest_delay") {
          return (
            (a.detection_delay_seconds ?? 999999) -
            (b.detection_delay_seconds ?? 999999)
          );
        }
        return 0;
      });
  }, [
    articles,
    articleSearch,
    articleCompFilter,
    articleMethodFilter,
    articleSort,
  ]);

  // ==========================================================
  // FILTERED COMPETITORS
  // ==========================================================
  const filteredCompetitors = useMemo(() => {
    if (!compSearch.trim()) return competitors;
    const q = compSearch.toLowerCase();
    return competitors.filter(
      (c) =>
        (c.name || "").toLowerCase().includes(q) ||
        (c.website_url || "").toLowerCase().includes(q)
    );
  }, [competitors, compSearch]);

  // ==========================================================
  // FILTERED LOGS
  // ==========================================================
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (
        logCompFilter !== "all" &&
        String(log.competitor_id) !== String(logCompFilter)
      ) {
        return false;
      }
      if (logStatusFilter === "success" && !log.success) return false;
      if (logStatusFilter === "failed" && log.success) return false;
      return true;
    });
  }, [logs, logCompFilter, logStatusFilter]);

  // ==========================================================
  // LOADING / ERROR SCREENS
  // ==========================================================
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Initializing ContentPulse Monitoring Platform...</p>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="error-screen">
        <AlertCircle size={48} />
        <h2>Backend Connection Failed</h2>
        <p>{error}</p>
        <button className="primary-button" onClick={loadDashboard}>
          <RefreshCw size={16} /> Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="app">
      {/* ======================================================
          SIDEBAR
      ====================================================== */}
      <aside className="sidebar">
        <div className="logo-section">
          <div className="logo-icon">
            <Activity size={22} color="white" />
          </div>
          <div>
            <h1>ContentPulse</h1>
            <span>Competitor Intelligence</span>
          </div>
        </div>

        <nav className="navigation">
          <div
            className={`nav-item ${activePage === "dashboard" ? "active" : ""}`}
            onClick={() => setActivePage("dashboard")}
          >
            <Activity size={18} />
            <span>Dashboard</span>
          </div>

          <div
            className={`nav-item ${
              activePage === "competitors" ? "active" : ""
            }`}
            onClick={() => setActivePage("competitors")}
          >
            <Globe size={18} />
            <span>Competitors</span>
          </div>

          <div
            className={`nav-item ${activePage === "articles" ? "active" : ""}`}
            onClick={() => setActivePage("articles")}
          >
            <FileText size={18} />
            <span>Articles</span>
          </div>

          <div
            className={`nav-item ${
              activePage === "monitoring" ? "active" : ""
            }`}
            onClick={() => setActivePage("monitoring")}
          >
            <Server size={18} />
            <span>Monitoring</span>
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="system-status">
            <span className="status-dot"></span>
            <div>
              <strong>Engine Online</strong>
              <small>Worker threads: 10 active</small>
            </div>
          </div>
        </div>
      </aside>

      {/* ======================================================
          MAIN CONTENT
      ====================================================== */}
      <main className="main-content">
        {/* TOAST / ALERTS */}
        {toast && (
          <div className={`toast-banner ${toast.type}`}>
            <div className="toast-content">
              {toast.type === "success" ? (
                <CheckCircle size={18} />
              ) : toast.type === "error" ? (
                <AlertCircle size={18} />
              ) : (
                <Info size={18} />
              )}
              <span>{toast.message}</span>
            </div>
            <button className="toast-close" onClick={() => setToast(null)}>
              <X size={16} />
            </button>
          </div>
        )}

        {error && (
          <div className="error-banner">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {/* PAGES */}
        {activePage === "dashboard" && (
          <DashboardView
            stats={stats}
            competitors={competitors}
            articles={articles}
            logs={logs}
            refreshing={refreshing}
            handleRefresh={handleRefresh}
            handleToggle={handleToggle}
            onOpenArticle={(art) => setSelectedArticle(art)}
            onOpenCompetitor={(comp) => handleOpenCompetitorDetail(comp)}
            onCheckNow={(id, name) => handleCheckNow(id, name)}
            checkingId={checkingCompetitorId}
          />
        )}

        {activePage === "competitors" && (
          <CompetitorsView
            competitors={filteredCompetitors}
            allCompetitors={competitors}
            compSearch={compSearch}
            setCompSearch={setCompSearch}
            handleToggle={handleToggle}
            onOpenAdd={() => setShowAddCompetitor(true)}
            onOpenEdit={(comp) => setEditingCompetitor({ ...comp })}
            onOpenDelete={(comp) => setDeletingCompetitor(comp)}
            onOpenDetail={(comp) => handleOpenCompetitorDetail(comp)}
            onCheckNow={(id, name) => handleCheckNow(id, name)}
            onCheckAll={handleCheckAllNow}
            checkingId={checkingCompetitorId}
            checkingAll={checkingAll}
            refreshing={refreshing}
            handleRefresh={handleRefresh}
          />
        )}

        {activePage === "articles" && (
          <ArticlesView
            articles={filteredArticles}
            allArticlesCount={articles.length}
            competitors={competitors}
            articleSearch={articleSearch}
            setArticleSearch={setArticleSearch}
            articleCompFilter={articleCompFilter}
            setArticleCompFilter={setArticleCompFilter}
            articleMethodFilter={articleMethodFilter}
            setArticleMethodFilter={setArticleMethodFilter}
            articleSort={articleSort}
            setArticleSort={setArticleSort}
            onOpenArticle={(art) => setSelectedArticle(art)}
            refreshing={refreshing}
            handleRefresh={handleRefresh}
          />
        )}

        {activePage === "monitoring" && (
          <MonitoringView
            stats={stats}
            competitors={competitors}
            logs={filteredLogs}
            allLogsCount={logs.length}
            logCompFilter={logCompFilter}
            setLogCompFilter={setLogCompFilter}
            logStatusFilter={logStatusFilter}
            setLogStatusFilter={setLogStatusFilter}
            handleToggle={handleToggle}
            onCheckNow={(id, name) => handleCheckNow(id, name)}
            checkingId={checkingCompetitorId}
            refreshing={refreshing}
            handleRefresh={handleRefresh}
          />
        )}
      </main>

      {/* ======================================================
          MODAL: ADD COMPETITOR
      ====================================================== */}
      {showAddCompetitor && (
        <div className="modal-overlay" onClick={() => !addingCompetitor && setShowAddCompetitor(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Add Competitor</h3>
                <p>ContentPulse will inspect and discover available RSS, sitemaps & articles.</p>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setShowAddCompetitor(false)}
                disabled={addingCompetitor}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleAddCompetitor}>
              <div className="modal-body">
                <label>
                  Competitor Name
                  <input
                    type="text"
                    required
                    placeholder="e.g. Stripe Engineering Blog"
                    value={newCompetitor.name}
                    onChange={(e) =>
                      setNewCompetitor({ ...newCompetitor, name: e.target.value })
                    }
                    disabled={addingCompetitor}
                  />
                </label>

                <label>
                  Website URL
                  <input
                    type="url"
                    required
                    placeholder="https://stripe.com"
                    value={newCompetitor.website_url}
                    onChange={(e) =>
                      setNewCompetitor({
                        ...newCompetitor,
                        website_url: e.target.value,
                      })
                    }
                    disabled={addingCompetitor}
                  />
                </label>

                <label>
                  Blog / News URL (Optional)
                  <input
                    type="url"
                    placeholder="https://stripe.com/blog"
                    value={newCompetitor.blog_url}
                    onChange={(e) =>
                      setNewCompetitor({
                        ...newCompetitor,
                        blog_url: e.target.value,
                      })
                    }
                    disabled={addingCompetitor}
                  />
                </label>

                <label>
                  Check Interval
                  <div className="interval-picker">
                    {[1, 2, 5, 10].map((m) => (
                      <button
                        key={m}
                        type="button"
                        className={`interval-btn${newCompetitor.check_interval_minutes === m ? " active" : ""}`}
                        onClick={() => setNewCompetitor({ ...newCompetitor, check_interval_minutes: m })}
                        disabled={addingCompetitor}
                      >
                        {m} min
                      </button>
                    ))}
                  </div>
                </label>

                <div className="analysis-info">
                  <Globe size={18} style={{ flexShrink: 0, marginTop: 2 }} />
                  <span>
                    Our auto-analyzer inspects standard RSS feeds, sitemap indexes, and direct article listings to configure monitoring.
                  </span>
                </div>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowAddCompetitor(false)}
                  disabled={addingCompetitor}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={addingCompetitor}
                >
                  {addingCompetitor ? "Analyzing Website..." : "Analyze & Add"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================
          MODAL: EDIT COMPETITOR
      ====================================================== */}
      {editingCompetitor && (
        <div
          className="modal-overlay"
          onClick={() => !savingEdit && setEditingCompetitor(null)}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Edit Competitor</h3>
                <p>Update competitor details and monitoring endpoints.</p>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setEditingCompetitor(null)}
                disabled={savingEdit}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveEditCompetitor}>
              <div className="modal-body">
                <label>
                  Competitor Name
                  <input
                    type="text"
                    required
                    value={editingCompetitor.name}
                    onChange={(e) =>
                      setEditingCompetitor({
                        ...editingCompetitor,
                        name: e.target.value,
                      })
                    }
                    disabled={savingEdit}
                  />
                </label>

                <label>
                  Website URL
                  <input
                    type="url"
                    required
                    value={editingCompetitor.website_url}
                    onChange={(e) =>
                      setEditingCompetitor({
                        ...editingCompetitor,
                        website_url: e.target.value,
                      })
                    }
                    disabled={savingEdit}
                  />
                </label>

                <label>
                  Blog URL
                  <input
                    type="url"
                    value={editingCompetitor.blog_url || ""}
                    onChange={(e) =>
                      setEditingCompetitor({
                        ...editingCompetitor,
                        blog_url: e.target.value,
                      })
                    }
                    disabled={savingEdit}
                  />
                </label>

                <label>
                  RSS Feed URL
                  <input
                    type="url"
                    placeholder="https://example.com/rss.xml"
                    value={editingCompetitor.rss_url || ""}
                    onChange={(e) =>
                      setEditingCompetitor({
                        ...editingCompetitor,
                        rss_url: e.target.value,
                      })
                    }
                    disabled={savingEdit}
                  />
                </label>

                <label>
                  Sitemap URL
                  <input
                    type="url"
                    placeholder="https://example.com/sitemap.xml"
                    value={editingCompetitor.sitemap_url || ""}
                    onChange={(e) =>
                      setEditingCompetitor({
                        ...editingCompetitor,
                        sitemap_url: e.target.value,
                      })
                    }
                    disabled={savingEdit}
                  />
                </label>

                <label>
                  Check Interval
                  <div className="interval-picker">
                    {[1, 2, 5, 10].map((m) => (
                      <button
                        key={m}
                        type="button"
                        className={`interval-btn${(editingCompetitor.check_interval_minutes || 1) === m ? " active" : ""}`}
                        onClick={() => setEditingCompetitor({ ...editingCompetitor, check_interval_minutes: m })}
                        disabled={savingEdit}
                      >
                        {m} min
                      </button>
                    ))}
                  </div>
                </label>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setEditingCompetitor(null)}
                  disabled={savingEdit}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={savingEdit}
                >
                  {savingEdit ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================
          MODAL: DELETE COMPETITOR CONFIRMATION
      ====================================================== */}
      {deletingCompetitor && (
        <div
          className="modal-overlay"
          onClick={() => !isDeleting && setDeletingCompetitor(null)}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3>Delete Competitor</h3>
                <p>Are you sure you want to delete this competitor?</p>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setDeletingCompetitor(null)}
                disabled={isDeleting}
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              <p style={{ margin: 0, fontSize: 13, color: "#475569" }}>
                Deleting <strong>{deletingCompetitor.name}</strong> will also remove its associated monitoring sources, articles, and logs. This action cannot be undone.
              </p>
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setDeletingCompetitor(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger-button"
                onClick={handleConfirmDeleteCompetitor}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete Competitor"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================
          MODAL: COMPETITOR DETAIL
      ====================================================== */}
      {selectedCompetitor && (
        <div
          className="modal-overlay"
          onClick={() => setSelectedCompetitor(null)}
        >
          <div
            className="modal large"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h3>{selectedCompetitor.name}</h3>
                <p>{selectedCompetitor.website_url}</p>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setSelectedCompetitor(null)}
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              {loadingDetail ? (
                <div className="empty-state">
                  <div className="loading-spinner"></div>
                  <p>Loading competitor details...</p>
                </div>
              ) : (
                <>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <strong>Status</strong>
                      <span>
                        <StatusBadge status={competitorDetailData?.status || selectedCompetitor.status} />
                      </span>
                    </div>
                    <div className="detail-item">
                      <strong>Monitoring</strong>
                      <span>
                        {selectedCompetitor.monitoring_enabled ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <div className="detail-item">
                      <strong>Last Checked</strong>
                      <span>{formatDate(competitorDetailData?.last_checked || selectedCompetitor.last_checked)}</span>
                    </div>
                    <div className="detail-item">
                      <strong>Total Articles Detected</strong>
                      <span>{competitorDetailData?.total_articles ?? 0}</span>
                    </div>
                  </div>

                  <h4 style={{ margin: "16px 0 8px", fontSize: 13, color: "#1e293b" }}>
                    Configured Monitoring Sources
                  </h4>
                  {competitorDetailData?.sources?.length > 0 ? (
                    <div className="table-container" style={{ border: "1px solid #e2e8f0", borderRadius: 8, marginBottom: 16 }}>
                      <table>
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>URL</th>
                            <th>Priority</th>
                            <th>Last Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {competitorDetailData.sources.map((src) => (
                            <tr key={src.id}>
                              <td>
                                <span className={`source-tag ${src.source_type}`}>
                                  {src.source_type}
                                </span>
                              </td>
                              <td>
                                <a
                                  href={src.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{ color: "#2563eb", textDecoration: "none", fontSize: 12 }}
                                >
                                  {src.source_url}
                                </a>
                              </td>
                              <td>Priority {src.priority}</td>
                              <td>
                                {src.last_success === true ? (
                                  <span style={{ color: "#16a34a", fontSize: 12, fontWeight: 600 }}>Active / Healthy</span>
                                ) : src.last_success === false ? (
                                  <span style={{ color: "#dc2626", fontSize: 12, fontWeight: 600 }}>Failed</span>
                                ) : (
                                  <span style={{ color: "#94a3b8", fontSize: 12 }}>Pending</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 16 }}>
                      No active RSS or sitemap sources configured.
                    </p>
                  )}

                  <h4 style={{ margin: "16px 0 8px", fontSize: 13, color: "#1e293b" }}>
                    Recent Detected Articles
                  </h4>
                  {competitorDetailData?.recent_articles?.length > 0 ? (
                    <div className="table-container" style={{ border: "1px solid #e2e8f0", borderRadius: 8 }}>
                      <table>
                        <thead>
                          <tr>
                            <th>Title</th>
                            <th>Detected</th>
                            <th>Delay</th>
                            <th>Method</th>
                          </tr>
                        </thead>
                        <tbody>
                          {competitorDetailData.recent_articles.map((art) => (
                            <tr key={art.id}>
                              <td>
                                <a
                                  href={art.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{ color: "#0f172a", textDecoration: "none", fontWeight: 500 }}
                                >
                                  {art.title}
                                </a>
                              </td>
                              <td>{formatDate(art.detected_at)}</td>
                              <td>{formatDelay(art.detection_delay_seconds)}</td>
                              <td>
                                <span className="method-badge">{art.detection_method}</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p style={{ fontSize: 12, color: "#94a3b8" }}>
                      No articles detected yet for this competitor.
                    </p>
                  )}
                </>
              )}
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setSelectedCompetitor(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================
          MODAL: ARTICLE DETAIL
      ====================================================== */}
      {selectedArticle && (
        <div
          className="modal-overlay"
          onClick={() => setSelectedArticle(null)}
        >
          <div
            className="modal large"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <span className="source-tag direct" style={{ marginBottom: 6, display: "inline-block" }}>
                  {selectedArticle.competitor_name || `Competitor #${selectedArticle.competitor_id}`}
                </span>
                <h3>{selectedArticle.title}</h3>
                <p>
                  <a
                    href={selectedArticle.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "#2563eb", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 4 }}
                  >
                    Open Original Article <ExternalLink size={12} />
                  </a>
                </p>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setSelectedArticle(null)}
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              {selectedArticle.featured_image_url && (
                <img
                  src={selectedArticle.featured_image_url}
                  alt={selectedArticle.title}
                  className="article-detail-img"
                  onError={(e) => {
                    e.target.style.display = "none";
                  }}
                />
              )}

              <div className="detail-grid">
                <div className="detail-item">
                  <strong>Author</strong>
                  <span>{selectedArticle.author || "Unknown"}</span>
                </div>
                <div className="detail-item">
                  <strong>Detection Method</strong>
                  <span style={{ textTransform: "uppercase" }}>{selectedArticle.detection_method || "Unknown"}</span>
                </div>
                <div className="detail-item">
                  <strong>Published At</strong>
                  <span>{formatDate(selectedArticle.published_at)}</span>
                </div>
                <div className="detail-item">
                  <strong>Detected At</strong>
                  <span>{formatDate(selectedArticle.detected_at)}</span>
                </div>
                <div className="detail-item">
                  <strong>Detection Delay</strong>
                  <span className="delay-pill fast">{formatDelay(selectedArticle.detection_delay_seconds)}</span>
                </div>
                <div className="detail-item">
                  <strong>Check ID</strong>
                  <span style={{ fontFamily: "monospace", fontSize: 11 }}>{selectedArticle.check_id || "—"}</span>
                </div>
              </div>

              {selectedArticle.canonical_url && (
                <div style={{ marginBottom: 16, fontSize: 12, color: "#64748b" }}>
                  <strong>Canonical URL: </strong>
                  <a href={selectedArticle.canonical_url} target="_blank" rel="noreferrer" style={{ color: "#2563eb" }}>
                    {selectedArticle.canonical_url}
                  </a>
                </div>
              )}

              {selectedArticle.categories?.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <strong style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                    Categories
                  </strong>
                  <div className="article-tags-row">
                    {selectedArticle.categories.map((c, i) => (
                      <span key={i} className="tag-badge" style={{ background: "#e0e7ff", color: "#3730a3" }}>
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedArticle.tags?.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <strong style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                    Tags
                  </strong>
                  <div className="article-tags-row">
                    {selectedArticle.tags.map((t, i) => (
                      <span key={i} className="tag-badge">
                        #{t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <h4 style={{ margin: "16px 0 8px", fontSize: 13, color: "#1e293b" }}>
                Article Body / Content
              </h4>
              <div className="article-detail-content">
                {selectedArticle.content || selectedArticle.content_preview || selectedArticle.meta_description || "No article text content extracted."}
              </div>

              {selectedArticle.relevant_links?.length > 0 && (
                <>
                  <h4 style={{ margin: "16px 0 8px", fontSize: 13, color: "#1e293b" }}>
                    Extracted Relevant Links ({selectedArticle.relevant_links.length})
                  </h4>
                  <div className="detail-links-list">
                    {selectedArticle.relevant_links.map((link, idx) => (
                      <a
                        key={idx}
                        href={link.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {link.text ? `${link.text} — ` : ""}{link.url}
                      </a>
                    ))}
                  </div>
                </>
              )}
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setSelectedArticle(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================
// DASHBOARD VIEW
// ============================================================
function DashboardView({
  stats,
  competitors,
  articles,
  logs,
  refreshing,
  handleRefresh,
  handleToggle,
  onOpenArticle,
  onOpenCompetitor,
  onCheckNow,
  checkingId,
}) {
  return (
    <>
      <header className="topbar">
        <div>
          <h2>Dashboard</h2>
          <p>Real-time competitor content monitoring & intelligence</p>
        </div>
        <div className="topbar-actions">
          <button
            className="refresh-button"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw size={15} className={refreshing ? "spinning" : ""} />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {/* SYSTEM RELIABILITY BAR */}
      <div className="reliability-card">
        <div className="reliability-info">
          <h4>
            <ShieldCheck size={18} /> Resilient Monitoring Engine Active
          </h4>
          <p>
            Automated background cycles with timeout safeguards, error isolation, and deduplication.
          </p>
        </div>
        <div className="reliability-tags">
          <span className="guard-tag">
            <Zap size={13} color="#38bdf8" /> 3 Retries w/ Exp. Backoff
          </span>
          <span className="guard-tag">
            <Clock size={13} color="#38bdf8" /> 15s Request Timeout
          </span>
          <span className="guard-tag">
            <Layers size={13} color="#38bdf8" /> 10 Concurrency Workers
          </span>
        </div>
      </div>

      {/* STAT CARDS */}
      <section className="stats-grid">
        <StatCard
          title="Monitored Competitors"
          value={stats?.total_competitors ?? 0}
          subtitle={`${stats?.enabled_competitors ?? 0} enabled • ${stats?.online_competitors ?? 0} online`}
          icon={<Globe size={20} />}
        />
        <StatCard
          title="Articles Detected"
          value={stats?.total_articles ?? 0}
          subtitle="Captured with full content"
          icon={<FileText size={20} />}
          iconClass="green"
        />
        <StatCard
          title="Average Detection"
          value={formatDelay(stats?.average_detection_delay_seconds)}
          subtitle={`Fastest: ${formatDelay(stats?.fastest_detection_delay_seconds)} • Slowest: ${formatDelay(stats?.slowest_detection_delay_seconds)}`}
          icon={<Clock size={20} />}
          iconClass="purple"
        />
        <StatCard
          title="Monitoring Success"
          value={`${stats?.success_rate_percent ?? 100}%`}
          subtitle={`${stats?.successful_checks ?? 0} ok • ${stats?.failed_checks ?? 0} failed (${stats?.total_checks ?? 0} total)`}
          icon={<Activity size={20} />}
          iconClass={stats?.failed_checks > 0 ? "amber" : "green"}
        />
      </section>

      {/* VISUAL CHARTS ROW */}
      <div className="two-col-grid">
        {/* Detection Performance Ranges */}
        <div className="chart-card">
          <div className="chart-card-header">
            <h4>Detection Delay Performance</h4>
            <span>Speed distribution from publication to system detection</span>
          </div>
          <div className="delay-bar-container">
            <div className="delay-bar-item">
              <div className="delay-bar-label">
                <span>&lt; 30 Seconds (Near Real-Time)</span>
                <strong>{stats?.delay_ranges?.under_30s ?? 0} articles</strong>
              </div>
              <div className="delay-bar-track">
                <div
                  className="delay-bar-fill fast"
                  style={{
                    width: `${
                      stats?.total_articles
                        ? ((stats?.delay_ranges?.under_30s ?? 0) / stats.total_articles) * 100
                        : 0
                    }%`,
                  }}
                ></div>
              </div>
            </div>

            <div className="delay-bar-item">
              <div className="delay-bar-label">
                <span>30s – 2 Minutes (Fast)</span>
                <strong>{stats?.delay_ranges?.["30s_to_2m"] ?? 0} articles</strong>
              </div>
              <div className="delay-bar-track">
                <div
                  className="delay-bar-fill medium"
                  style={{
                    width: `${
                      stats?.total_articles
                        ? ((stats?.delay_ranges?.["30s_to_2m"] ?? 0) / stats.total_articles) * 100
                        : 0
                    }%`,
                  }}
                ></div>
              </div>
            </div>

            <div className="delay-bar-item">
              <div className="delay-bar-label">
                <span>2 – 10 Minutes (Standard)</span>
                <strong>{stats?.delay_ranges?.["2m_to_10m"] ?? 0} articles</strong>
              </div>
              <div className="delay-bar-track">
                <div
                  className="delay-bar-fill warning"
                  style={{
                    width: `${
                      stats?.total_articles
                        ? ((stats?.delay_ranges?.["2m_to_10m"] ?? 0) / stats.total_articles) * 100
                        : 0
                    }%`,
                  }}
                ></div>
              </div>
            </div>

            <div className="delay-bar-item">
              <div className="delay-bar-label">
                <span>&gt; 10 Minutes (Batch Sitemaps)</span>
                <strong>{stats?.delay_ranges?.over_10m ?? 0} articles</strong>
              </div>
              <div className="delay-bar-track">
                <div
                  className="delay-bar-fill slow"
                  style={{
                    width: `${
                      stats?.total_articles
                        ? ((stats?.delay_ranges?.over_10m ?? 0) / stats.total_articles) * 100
                        : 0
                    }%`,
                  }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Top Competitors by Articles */}
        <div className="chart-card">
          <div className="chart-card-header">
            <h4>Top Monitored Competitors</h4>
            <span>Total discovered articles by competitor</span>
          </div>
          <div className="competitor-rank-list">
            {stats?.articles_by_competitor?.length > 0 ? (
              stats.articles_by_competitor.map((comp) => {
                const maxCount = stats.articles_by_competitor[0].count || 1;
                const pct = Math.max(12, (comp.count / maxCount) * 100);
                return (
                  <div key={comp.competitor_id} className="competitor-rank-item">
                    <div className="competitor-rank-name" title={comp.competitor_name}>
                      {comp.competitor_name}
                    </div>
                    <div className="competitor-rank-bar">
                      <div className="competitor-rank-fill" style={{ width: `${pct}%` }}></div>
                    </div>
                    <div className="competitor-rank-count">{comp.count} arts</div>
                  </div>
                );
              })
            ) : (
              <div className="empty-state" style={{ padding: 20 }}>
                <p>No competitor articles recorded yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* RECENTLY DETECTED ARTICLES */}
      <section className="dashboard-section">
        <div className="section-header">
          <div>
            <h3>
              <FileText size={16} color="#2563eb" /> Recently Detected Articles
            </h3>
            <p>Latest publications discovered across competitors</p>
          </div>
          <span className="section-count">{articles.length} total articles</span>
        </div>
        <ArticleList articles={articles.slice(0, 6)} onOpenArticle={onOpenArticle} />
      </section>

      {/* COMPETITOR MONITORING STATUS */}
      <section className="dashboard-section">
        <div className="section-header">
          <div>
            <h3>
              <Globe size={16} color="#2563eb" /> Competitor Status Overview
            </h3>
            <p>Live health and background schedule status</p>
          </div>
          <span className="section-count">{competitors.length} competitors</span>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Competitor</th>
                <th>Health</th>
                <th>Sources</th>
                <th>Last Check</th>
                <th>Last Detection</th>
                <th>Monitoring</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {competitors.slice(0, 8).map((competitor) => (
                <tr key={competitor.id}>
                  <td>
                    <div className="competitor-name">
                      <div className="competitor-icon">
                        <Globe size={16} />
                      </div>
                      <div>
                        <strong>{competitor.name}</strong>
                        <small>{competitor.website_url}</small>
                      </div>
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={competitor.status} />
                  </td>
                  <td>
                    <div className="source-badges">
                      {competitor.rss_url && <span className="source-tag rss">RSS</span>}
                      {competitor.sitemap_url && <span className="source-tag sitemap">Sitemap</span>}
                      {competitor.blog_url && <span className="source-tag direct">Direct</span>}
                      {!competitor.rss_url && !competitor.sitemap_url && !competitor.blog_url && (
                        <span className="source-tag">No Source</span>
                      )}
                    </div>
                  </td>
                  <td>{formatDate(competitor.last_checked)}</td>
                  <td>{formatDate(competitor.last_successful_detection)}</td>
                  <td>
                    <button
                      className={competitor.monitoring_enabled ? "toggle active" : "toggle"}
                      onClick={() => handleToggle(competitor.id, competitor.monitoring_enabled)}
                    >
                      <span></span>
                      {competitor.monitoring_enabled ? "ON" : "OFF"}
                    </button>
                  </td>
                  <td>
                    <div className="table-actions">
                      <button
                        className="action-icon-btn"
                        title="Check Now"
                        disabled={checkingId === competitor.id}
                        onClick={() => onCheckNow(competitor.id, competitor.name)}
                      >
                        <Play size={13} className={checkingId === competitor.id ? "spinning" : ""} />
                      </button>
                      <button
                        className="action-icon-btn"
                        title="View Details"
                        onClick={() => onOpenCompetitor(competitor)}
                      >
                        <Eye size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

// ============================================================
// COMPETITORS VIEW
// ============================================================
function CompetitorsView({
  competitors,
  allCompetitors,
  compSearch,
  setCompSearch,
  handleToggle,
  onOpenAdd,
  onOpenEdit,
  onOpenDelete,
  onOpenDetail,
  onCheckNow,
  onCheckAll,
  checkingId,
  checkingAll,
  refreshing,
  handleRefresh,
}) {
  return (
    <>
      <header className="topbar">
        <div>
          <h2>Competitors</h2>
          <p>Manage competitor websites, discovery sources and schedules</p>
        </div>
        <div className="topbar-actions">
          <button className="refresh-button" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw size={15} className={refreshing ? "spinning" : ""} />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
          <button
            className="refresh-button"
            onClick={onCheckAll}
            disabled={checkingAll}
            style={{ color: checkingAll ? "#64748b" : "#0ea5e9" }}
            title="Immediately scan all enabled competitors for new articles"
          >
            <Zap size={15} className={checkingAll ? "spinning" : ""} />
            {checkingAll ? "Scanning All…" : "Scan All Now"}
          </button>
          <button className="primary-button" onClick={onOpenAdd}>
            + Add Competitor
          </button>
        </div>
      </header>

      {/* TOOLBAR */}
      <div className="toolbar">
        <div className="search-box">
          <Search size={16} color="#94a3b8" />
          <input
            type="text"
            placeholder="Search competitors by name or URL..."
            value={compSearch}
            onChange={(e) => setCompSearch(e.target.value)}
          />
          {compSearch && (
            <button
              onClick={() => setCompSearch("")}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}
            >
              <X size={14} />
            </button>
          )}
        </div>
        <div className="filter-group">
          <span style={{ fontSize: 12, color: "#64748b" }}>
            Showing {competitors.length} of {allCompetitors.length} competitors
          </span>
        </div>
      </div>

      {/* TABLE */}
      <section className="dashboard-section">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Competitor</th>
                <th>Status</th>
                <th>Sources</th>
                <th>Last Check</th>
                <th>Last Detection</th>
                <th>Monitoring</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {competitors.length > 0 ? (
                competitors.map((competitor) => (
                  <tr key={competitor.id}>
                    <td>
                      <div className="competitor-name">
                        <div className="competitor-icon">
                          <Globe size={16} />
                        </div>
                        <div>
                          <strong>{competitor.name}</strong>
                          <small title={competitor.website_url}>{competitor.website_url}</small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={competitor.status} />
                    </td>
                    <td>
                      <div className="source-badges">
                        {competitor.rss_url && <span className="source-tag rss">RSS</span>}
                        {competitor.sitemap_url && <span className="source-tag sitemap">Sitemap</span>}
                        {competitor.blog_url && <span className="source-tag direct">Direct</span>}
                        {!competitor.rss_url && !competitor.sitemap_url && !competitor.blog_url && (
                          <span className="source-tag">None</span>
                        )}
                      </div>
                    </td>
                    <td>{formatDate(competitor.last_checked)}</td>
                    <td>{formatDate(competitor.last_successful_detection)}</td>
                    <td>
                      <button
                        className={competitor.monitoring_enabled ? "toggle active" : "toggle"}
                        onClick={() => handleToggle(competitor.id, competitor.monitoring_enabled)}
                      >
                        <span></span>
                        {competitor.monitoring_enabled ? "ON" : "OFF"}
                      </button>
                    </td>
                    <td>
                      <div className="table-actions">
                        <button
                          className="action-icon-btn"
                          title="Trigger Check Now"
                          disabled={checkingId === competitor.id}
                          onClick={() => onCheckNow(competitor.id, competitor.name)}
                        >
                          <Play size={13} className={checkingId === competitor.id ? "spinning" : ""} />
                        </button>
                        <button
                          className="action-icon-btn"
                          title="View Details"
                          onClick={() => onOpenDetail(competitor)}
                        >
                          <Eye size={13} />
                        </button>
                        <button
                          className="action-icon-btn"
                          title="Edit Competitor"
                          onClick={() => onOpenEdit(competitor)}
                        >
                          <Edit3 size={13} />
                        </button>
                        <button
                          className="action-icon-btn delete"
                          title="Delete Competitor"
                          onClick={() => onOpenDelete(competitor)}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7}>
                    <div className="empty-state">
                      <Globe size={32} />
                      <p>No competitors found matching your search.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

// ============================================================
// ARTICLES VIEW
// ============================================================
function ArticlesView({
  articles,
  allArticlesCount,
  competitors,
  articleSearch,
  setArticleSearch,
  articleCompFilter,
  setArticleCompFilter,
  articleMethodFilter,
  setArticleMethodFilter,
  articleSort,
  setArticleSort,
  onOpenArticle,
  refreshing,
  handleRefresh,
}) {
  return (
    <>
      <header className="topbar">
        <div>
          <h2>Articles</h2>
          <p>Discovered competitor content with full extracted body, metadata & delays</p>
        </div>
        <div className="topbar-actions">
          <button className="refresh-button" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw size={15} className={refreshing ? "spinning" : ""} />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {/* FILTERS & SEARCH TOOLBAR */}
      <div className="toolbar">
        <div className="search-box">
          <Search size={16} color="#94a3b8" />
          <input
            type="text"
            placeholder="Search articles by title, author, url..."
            value={articleSearch}
            onChange={(e) => setArticleSearch(e.target.value)}
          />
          {articleSearch && (
            <button
              onClick={() => setArticleSearch("")}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className="filter-group">
          <select
            className="filter-select"
            value={articleCompFilter}
            onChange={(e) => setArticleCompFilter(e.target.value)}
          >
            <option value="all">All Competitors</option>
            {competitors.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <select
            className="filter-select"
            value={articleMethodFilter}
            onChange={(e) => setArticleMethodFilter(e.target.value)}
          >
            <option value="all">All Methods</option>
            <option value="rss">RSS Feed</option>
            <option value="sitemap">Sitemap</option>
            <option value="direct_page">Direct Page</option>
          </select>

          <select
            className="filter-select"
            value={articleSort}
            onChange={(e) => setArticleSort(e.target.value)}
          >
            <option value="newest_detected">Newest Detected</option>
            <option value="oldest_detected">Oldest Detected</option>
            <option value="newest_published">Newest Published</option>
            <option value="fastest_delay">Fastest Detection</option>
          </select>
        </div>
      </div>

      {/* ARTICLE LISTING */}
      <section className="dashboard-section">
        <div className="section-header">
          <div>
            <h3>
              <FileText size={16} color="#2563eb" /> Detected Content Feed
            </h3>
            <p>
              Showing {articles.length} of {allArticlesCount} articles
            </p>
          </div>
        </div>

        <ArticleList articles={articles} onOpenArticle={onOpenArticle} />
      </section>
    </>
  );
}

// ============================================================
// MONITORING VIEW
// ============================================================
function MonitoringView({
  stats,
  competitors,
  logs,
  allLogsCount,
  logCompFilter,
  setLogCompFilter,
  logStatusFilter,
  setLogStatusFilter,
  handleToggle,
  onCheckNow,
  checkingId,
  refreshing,
  handleRefresh,
}) {
  return (
    <>
      <header className="topbar">
        <div>
          <h2>Monitoring & Observability</h2>
          <p>Live health, background checks, response latencies and reliability</p>
        </div>
        <div className="topbar-actions">
          <button className="refresh-button" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw size={15} className={refreshing ? "spinning" : ""} />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {/* PERFORMANCE METRICS */}
      <section className="stats-grid">
        <StatCard
          title="Avg Response Latency"
          value={formatMs(stats?.average_response_time_ms)}
          subtitle={`Fastest: ${formatMs(stats?.fastest_response_time_ms)} • Slowest: ${formatMs(stats?.slowest_response_time_ms)}`}
          icon={<Clock size={20} />}
          iconClass="purple"
        />
        <StatCard
          title="Total Check Cycles"
          value={stats?.total_checks ?? 0}
          subtitle={`${stats?.successful_checks ?? 0} successful • ${stats?.failed_checks ?? 0} errors`}
          icon={<Server size={20} />}
          iconClass="green"
        />
        <StatCard
          title="Engine Success Rate"
          value={`${stats?.success_rate_percent ?? 100}%`}
          subtitle="Pass rate across all sources"
          icon={<CheckCircle size={20} />}
          iconClass={stats?.failed_checks > 0 ? "amber" : "green"}
        />
        <StatCard
          title="No-Source Sites"
          value={stats?.no_source_competitors ?? 0}
          subtitle="Requires valid RSS/sitemap"
          icon={<AlertTriangle size={20} />}
          iconClass="amber"
        />
      </section>

      {/* COMPETITORS LIVE STATUS */}
      <section className="dashboard-section">
        <div className="section-header">
          <div>
            <h3>
              <Globe size={16} color="#2563eb" /> Competitor Monitoring Health
            </h3>
            <p>Direct live status and manual trigger per competitor</p>
          </div>
          <span className="section-count">{competitors.length} sites</span>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Competitor</th>
                <th>Health Status</th>
                <th>Sources</th>
                <th>Last Checked</th>
                <th>Monitoring</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {competitors.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div className="competitor-name">
                      <div className="competitor-icon">
                        <Globe size={16} />
                      </div>
                      <div>
                        <strong>{c.name}</strong>
                        <small>{c.website_url}</small>
                      </div>
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td>
                    <div className="source-badges">
                      {c.rss_url && <span className="source-tag rss">RSS</span>}
                      {c.sitemap_url && <span className="source-tag sitemap">Sitemap</span>}
                      {c.blog_url && <span className="source-tag direct">Direct</span>}
                    </div>
                  </td>
                  <td>{formatDate(c.last_checked)}</td>
                  <td>
                    <button
                      className={c.monitoring_enabled ? "toggle active" : "toggle"}
                      onClick={() => handleToggle(c.id, c.monitoring_enabled)}
                    >
                      <span></span>
                      {c.monitoring_enabled ? "ON" : "OFF"}
                    </button>
                  </td>
                  <td>
                    <button
                      className="primary-button"
                      style={{ padding: "5px 10px", fontSize: 11 }}
                      disabled={checkingId === c.id}
                      onClick={() => onCheckNow(c.id, c.name)}
                    >
                      <Play size={11} className={checkingId === c.id ? "spinning" : ""} />
                      {checkingId === c.id ? "Checking..." : "Check Now"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* LOGS TABLE WITH FILTERS */}
      <div className="toolbar">
        <div className="filter-group">
          <select
            className="filter-select"
            value={logCompFilter}
            onChange={(e) => setLogCompFilter(e.target.value)}
          >
            <option value="all">All Competitors</option>
            {competitors.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          <select
            className="filter-select"
            value={logStatusFilter}
            onChange={(e) => setLogStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="success">Successful Checks Only</option>
            <option value="failed">Failed Checks Only</option>
          </select>
        </div>

        <span style={{ fontSize: 12, color: "#64748b" }}>
          Showing {logs.length} of {allLogsCount} records
        </span>
      </div>

      <section className="dashboard-section">
        <div className="section-header">
          <div>
            <h3>
              <Server size={16} color="#2563eb" /> Recent Monitoring Activity Logs
            </h3>
            <p>Historical execution timeline with latency and discovery results</p>
          </div>
        </div>

        <ActivityList logs={logs} />
      </section>
    </>
  );
}

// ============================================================
// ARTICLE LIST COMPONENT
// ============================================================
function ArticleList({ articles, onOpenArticle }) {
  if (articles.length === 0) {
    return (
      <div className="empty-state">
        <FileText size={32} />
        <p>No articles found matching the current criteria.</p>
      </div>
    );
  }

  return (
    <div className="article-list">
      {articles.map((article) => (
        <div className="article-card" key={article.id}>
          {article.featured_image_url ? (
            <img
              src={article.featured_image_url}
              alt=""
              className="article-thumb"
              onError={(e) => {
                e.target.style.display = "none";
              }}
            />
          ) : (
            <div className="article-icon-box">
              <FileText size={20} />
            </div>
          )}

          <div className="article-info">
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: "#2563eb",
                marginBottom: 2,
                display: "inline-block",
              }}
            >
              {article.competitor_name || `Competitor #${article.competitor_id}`}
            </span>

            <a
              href="#view"
              className="article-title-link"
              onClick={(e) => {
                e.preventDefault();
                onOpenArticle(article);
              }}
            >
              {article.title}
            </a>

            {article.content_preview && (
              <p className="article-preview-text">{article.content_preview}</p>
            )}

            <div className="article-meta">
              <span>{article.author ? `By ${article.author}` : "Author: Unknown"}</span>
              <span>•</span>
              <span>Published: {formatDate(article.published_at)}</span>
              <span>•</span>
              <span>Detected: {formatDate(article.detected_at)}</span>
            </div>

            {(article.categories?.length > 0 || article.tags?.length > 0) && (
              <div className="article-tags-row">
                {article.categories?.slice(0, 2).map((cat, i) => (
                  <span key={i} className="tag-badge" style={{ background: "#e0e7ff", color: "#3730a3" }}>
                    {cat}
                  </span>
                ))}
                {article.tags?.slice(0, 3).map((tag, i) => (
                  <span key={i} className="tag-badge">
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="article-delay">
            <span className="delay-pill fast">{formatDelay(article.detection_delay_seconds)}</span>
            <small>detection delay</small>
            <div style={{ marginTop: 6 }}>
              <span className="method-badge">{article.detection_method || "direct"}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================
// ACTIVITY LIST COMPONENT
// ============================================================
function ActivityList({ logs }) {
  if (logs.length === 0) {
    return (
      <div className="empty-state">
        <Server size={32} />
        <p>No activity logs recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="activity-list">
      {logs.map((log) => (
        <div className="activity-row" key={log.id}>
          <div className="activity-status">
            {log.success ? (
              <CheckCircle size={18} className="success-icon" />
            ) : (
              <XCircle size={18} className="failure-icon" />
            )}
          </div>

          <div className="activity-info">
            <strong>
              {log.competitor_name || `Competitor #${log.competitor_id}`}
            </strong>
            {log.success ? (
              <span>
                {log.articles_found ?? 0} article(s) discovered during cycle
              </span>
            ) : (
              <span className="error-msg">
                {log.error_message || "Monitoring check failed"}
              </span>
            )}
          </div>

          <div className="activity-time">
            <span
              className={`response-badge ${
                (log.response_time_ms || 0) < 500
                  ? "fast"
                  : (log.response_time_ms || 0) > 3000
                  ? "slow"
                  : ""
              }`}
            >
              {log.response_time_ms ?? 0} ms
            </span>
            <span>{formatDate(log.checked_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================
// STAT CARD COMPONENT
// ============================================================
function StatCard({ title, value, subtitle, icon, iconClass = "" }) {
  return (
    <div className="stat-card">
      <div className="stat-card-top">
        <div className={`stat-icon ${iconClass}`}>{icon}</div>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-title">{title}</div>
      <div className="stat-subtitle">{subtitle}</div>
    </div>
  );
}

// ============================================================
// STATUS BADGE COMPONENT
// ============================================================
function StatusBadge({ status }) {
  const norm = (status || "unknown").toLowerCase();
  if (norm === "online") {
    return (
      <span className="status-badge online">
        <span></span> Online
      </span>
    );
  }
  if (norm === "offline") {
    return (
      <span className="status-badge offline">
        <span></span> Offline
      </span>
    );
  }
  if (norm === "no_source" || norm === "no source") {
    return (
      <span className="status-badge no-source">
        <span></span> No Source
      </span>
    );
  }
  return (
    <span className="status-badge unknown">
      <span></span> Unknown
    </span>
  );
}

// ============================================================
// FORMAT HELPERS
// ============================================================
function formatDate(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleString("en-IN", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return "—";
  }
}

function formatDelay(seconds) {
  if (seconds === null || seconds === undefined || seconds < 0) return "—";
  if (seconds < 60) return `${Number(seconds).toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function formatMs(ms) {
  if (ms === null || ms === undefined || ms < 0) return "—";
  return `${Math.round(ms)} ms`;
}

export default App;