import api from "./api";

export async function login(username, password) {
  const response = await api.post("/auth/login", {
    username,
    password,
  });

  return response.data;
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
}

export function getToken() {
  return localStorage.getItem("access_token");
}

export function getStoredUser() {
  const user = localStorage.getItem("user");

  if (!user) {
    return null;
  }

  try {
    return JSON.parse(user);
  } catch {
    return null;
  }
}