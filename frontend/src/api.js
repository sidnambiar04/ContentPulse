import axios from "axios";

const getBaseUrl = () => {
    // 1. Explicit environment variable (from Vite build or .env)
    const envUrl = import.meta.env.VITE_API_URL;
    if (envUrl && envUrl.trim() !== "") {
        if (envUrl.startsWith("http://") || envUrl.startsWith("https://")) {
            return envUrl.replace(/\/+$/, "");
        }
        return `https://${envUrl}`.replace(/\/+$/, "");
    }

    // 2. Automatic cloud host resolution (e.g. Render deployments)
    if (typeof window !== "undefined" && window.location.hostname.includes("onrender.com")) {
        const backendHost = window.location.hostname.replace("-frontend", "-backend");
        return `https://${backendHost}`;
    }

    // 3. Localhost fallback
    return "http://127.0.0.1:8000";
};

const API = axios.create({
    baseURL: getBaseUrl(),
    timeout: 60000,
});

export const getDashboardStats = async () => {
    const response = await API.get("/dashboard/stats");
    return response.data;
};

export const getCompetitors = async () => {
    const response = await API.get("/competitors");
    return response.data;
};

export const getCompetitorDetail = async (competitorId) => {
    const response = await API.get(`/competitors/${competitorId}`);
    return response.data;
};

export const createCompetitor = async (competitor) => {
    const response = await API.post("/competitors", competitor);
    return response.data;
};

export const updateCompetitor = async (competitorId, monitoringEnabled) => {
    const response = await API.patch(
        `/competitors/${competitorId}`,
        null,
        {
            params: {
                monitoring_enabled: monitoringEnabled,
            },
        }
    );
    return response.data;
};

export const updateCompetitorDetails = async (competitorId, data) => {
    const response = await API.patch(`/competitors/${competitorId}`, data);
    return response.data;
};

export const deleteCompetitor = async (competitorId) => {
    const response = await API.delete(`/competitors/${competitorId}`);
    return response.data;
};

export const checkCompetitorNow = async (competitorId) => {
    const response = await API.post(`/competitors/${competitorId}/check`);
    return response.data;
};

export const checkAllNow = async () => {
    const response = await API.post("/competitors/check-all");
    return response.data;
};

export const getArticles = async (params = {}) => {
    const response = await API.get("/articles", { params });
    return response.data;
};

export const getArticle = async (articleId) => {
    const response = await API.get(`/articles/${articleId}`);
    return response.data;
};

export const getMonitoringLogs = async (params = {}) => {
    const response = await API.get("/monitoring/logs", { params });
    return response.data;
};