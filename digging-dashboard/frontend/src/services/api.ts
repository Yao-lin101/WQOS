/**
 * API 客户端配置
 */

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';

// API基础配置
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8088/api';

// 创建axios实例
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加认证头
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    // 处理401错误 - 令牌过期或无效
    if (error.response?.status === 401) {
      // 清除本地存储的认证信息
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // 重定向到登录页面
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    // 处理其他HTTP错误
    if (error.response) {
      // 服务器返回的错误
      const errorData = error.response.data as any;
      const errorMessage = errorData?.message || errorData?.detail || '请求失败';
      console.error('API Error:', {
        status: error.response.status,
        message: errorMessage,
        url: error.config?.url,
      });
    } else if (error.request) {
      // 网络错误
      console.error('Network Error:', error.message);
    } else {
      // 其他错误
      console.error('Request Error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export { api, API_BASE_URL };
export const apiClient = api;

// 通用API响应类型
export interface APIResponse<T = any> {
  data: T;
  message?: string;
  success?: boolean;
}

// 通用错误类型
export interface APIError {
  error: string;
  message: string;
  details?: any;
}
