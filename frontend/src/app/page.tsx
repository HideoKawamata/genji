"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, ScrollText, BookOpen, Trash2, History, User, LogOut, Key, Mail, ShieldAlert } from "lucide-react";

type ConsultResponse = {
  character: string;
  message: string;
  explanation: string;
  waka: string;
  waka_translation: string;
  image_url: string;
};

type HistoryItem = ConsultResponse & {
  id: string;
  concern: string;
  timestamp: string;
};

type UserProfile = {
  email: string;
  avatar: string;
};

const AVATARS = [
  { id: "genji", name: "光源氏", file: "/avatars/avatar_genji.png" },
  { id: "murasaki", name: "紫の上", file: "/avatars/avatar_murasaki.png" },
  { id: "mikado", name: "帝 (天皇)", file: "/avatars/avatar_mikado.png" },
  { id: "rokujo", name: "六条御息所", file: "/avatars/avatar_rokujo.png" },
];

export default function Home() {
  const [concern, setConcern] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ConsultResponse | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // 認証関連の状態
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  
  // モーダル関連の状態
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register" | "forgot" | "reset">("login");
  const [isGoogleLogin, setIsGoogleLogin] = useState(false);
  const [showAvatarModal, setShowAvatarModal] = useState(false);
  
  // 入力フォームの状態
  const [emailInput, setEmailInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [confirmPasswordInput, setConfirmPasswordInput] = useState("");
  const [resetTokenInput, setResetTokenInput] = useState("");
  const [authError, setAuthError] = useState("");
  const [authMessage, setAuthMessage] = useState("");
  const [demoResetToken, setDemoResetToken] = useState(""); // デモ確認用

  // トースト表示用の状態
  const [toast, setToast] = useState<string | null>(null);

  // PDFダウンロード対象のRef
  const cardRef = useRef<HTMLDivElement>(null);

  const showToast = (message: string) => {
    setToast(message);
    setTimeout(() => setToast(null), 3500);
  };

  // 初期化および認証状態のロード
  useEffect(() => {
    // 履歴ロード
    const storedHistory = localStorage.getItem("genji_history");
    if (storedHistory) {
      try {
        setHistory(JSON.parse(storedHistory));
      } catch (e) {
        console.error("Failed to load history:", e);
      }
    }

    // トークンチェック
    const storedToken = localStorage.getItem("genji_token");
    if (storedToken) {
      setToken(storedToken);
      fetchUserProfile(storedToken);
    }
  }, []);

  const fetchUserProfile = async (authToken: string) => {
    try {
      const response = await fetch("/api/auth/me", {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
      } else {
        handleLogout();
      }
    } catch (e) {
      console.error("Profile fetch failed:", e);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("genji_token");
    setToken(null);
    setUser(null);
    showToast("雅なる世界からログアウトしました。");
  };

  // 認証処理
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    setAuthMessage("");

    let endpoint: string = authMode;
    if (isGoogleLogin) {
      endpoint = "google";
    } else if (authMode === "forgot") {
      endpoint = "forgot-password";
    } else if (authMode === "reset") {
      endpoint = "reset-password";
    }

    try {
      // バリデーション
      if (authMode === "register" && passwordInput !== confirmPasswordInput) {
        setAuthError("パスワードが一致しません。");
        return;
      }

      let payload = {};
      let url = `/api/auth/${endpoint}`;

      if (endpoint === "google") {
        if (!emailInput.endsWith("@gmail.com")) {
          setAuthError("Googleログインには @gmail.com 形式のアドレスが必要です。");
          return;
        }
        payload = {
          email: emailInput,
          token: "simulated_google_token_" + Math.random().toString(36).substring(7)
        };
      } else if (authMode === "forgot") {
        payload = { email: emailInput };
      } else if (authMode === "reset") {
        payload = {
          email: emailInput,
          token: resetTokenInput,
          new_password: passwordInput
        };
      } else {
        payload = {
          email: emailInput,
          password: passwordInput
        };
      }

      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        setAuthError(data.detail || "エラーが発生しました。");
        return;
      }

      // レスポンス処理
      if (authMode === "forgot") {
        setAuthMessage(data.message);
        if (data.demo_token) {
          setDemoResetToken(data.demo_token);
        }
        setAuthMode("reset");
      } else if (authMode === "reset") {
        showToast("パスワードが更新されました。ログインしてください。");
        setAuthMode("login");
        setPasswordInput("");
        setConfirmPasswordInput("");
        setResetTokenInput("");
      } else {
        // ログイン / 新規登録 / Googleログイン
        if (authMode === "register") {
          showToast("登録が完了しました！ログインしてください。");
          setAuthMode("login");
          setPasswordInput("");
        } else {
          // ログイン成功 (通常ログイン、Googleログイン)
          localStorage.setItem("genji_token", data.token);
          setToken(data.token);
          setUser(data.user);
          setShowAuthModal(false);
          resetAuthForm();
          showToast("無事にログインいたしました。");
        }
      }
    } catch (err) {
      console.error(err);
      setAuthError("認証サーバーとの通信に失敗しました。");
    }
  };

  const resetAuthForm = () => {
    setEmailInput("");
    setPasswordInput("");
    setConfirmPasswordInput("");
    setResetTokenInput("");
    setAuthError("");
    setAuthMessage("");
    setDemoResetToken("");
  };

  // アバター変更処理
  const handleSelectAvatar = async (avatarId: string) => {
    if (!token) return;
    try {
      const response = await fetch("/api/auth/profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ avatar: avatarId }),
      });

      if (response.ok) {
        const data = await response.json();
        if (user) {
          setUser({ ...user, avatar: data.avatar });
        }
        setShowAvatarModal(false);
        showToast(`アバターを「${AVATARS.find(a => a.id === avatarId)?.name}」に変更しました。`);
      } else {
        showToast("アバターの更新に失敗しました。");
      }
    } catch (e) {
      console.error(e);
      showToast("サーバーとの通信に失敗しました。");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!concern.trim()) return;

    setIsLoading(true);
    setError("");
    setResult(null);

    try {
      // 【実装の意図（タイムアウト回避）】
      // Next.jsのローカル開発サーバー(next dev)の内蔵プロキシはタイムアウト設定が短く、
      // HyDE + Gemini + Imagen の一連の処理（約30秒〜）が完了する前に通信を切断してしまいます。
      // これを回避するため、フロントエンドからバックエンドAPIへ直接通信(Direct Fetch)を行います。
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${apiUrl}/api/consult`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ concern }),
      });

      if (!response.ok) {
        throw new Error("通信エラーが発生しました");
      }

      const data = await response.json();
      setResult(data);

      // 履歴に保存
      const newItem: HistoryItem = {
        ...data,
        id: Math.random().toString(36).substring(2, 9),
        concern: concern,
        timestamp: new Date().toLocaleString("ja-JP", {
          month: "numeric",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      const updatedHistory = [newItem, ...history];
      setHistory(updatedHistory);
      localStorage.setItem("genji_history", JSON.stringify(updatedHistory));

    } catch (err) {
      console.error(err);
      setError("神託を得られませんでした。バックエンドサーバーが起動しているか確認してください。");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteHistory = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const updated = history.filter((item) => item.id !== id);
    setHistory(updated);
    localStorage.setItem("genji_history", JSON.stringify(updated));
  };

  const handleLoadHistory = (item: HistoryItem) => {
    setResult({
      character: item.character,
      message: item.message,
      explanation: item.explanation,
      waka: item.waka,
      waka_translation: item.waka_translation,
      image_url: item.image_url,
    });
    setConcern(item.concern);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // PDFダウンロード処理
  const downloadPDF = async () => {
    const cardElement = cardRef.current;
    if (!cardElement) return;

    try {
      showToast("神託の書（PDF）を調製しております。少々お待ちください...");
      const { toPng } = await import("html-to-image");
      const jsPDF = (await import("jspdf")).jsPDF;

      const imgData = await toPng(cardElement, {
        quality: 0.95,
        pixelRatio: 2,
        backgroundColor: "#f4e9d8",
      });

      const imgWidth = 210; // 基準の横幅 mm
      const imgHeight = (cardElement.offsetHeight * imgWidth) / cardElement.offsetWidth;
      
      const pdf = new jsPDF({
        orientation: "p",
        unit: "mm",
        format: [imgWidth, imgHeight]
      });
      
      pdf.addImage(imgData, "PNG", 0, 0, imgWidth, imgHeight);
      pdf.save(`genji_mirror_${result?.character || "shintaku"}.pdf`);
      showToast("神託の書（PDF）がダウンロードされました。");
    } catch (e) {
      console.error(e);
      showToast("PDFの出力に失敗しました。");
    }
  };

  // SNS共有処理
  const handleShare = (platform: string) => {
    if (!result) return;
    
    const text = `【源氏鏡】の神託を得ました。現代の悩みに、千年前の${result.character}が寄り添います。\n\n和歌：${result.waka}\n「${result.message}」\n#源氏鏡 #源氏物語`;
    const shareUrl = window.location.href;

    if (platform === "x") {
      window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`, "_blank");
    } else if (platform === "facebook") {
      window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`, "_blank");
    } else if (platform === "linkedin") {
      window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`, "_blank");
    } else if (platform === "instagram") {
      // InstagramはAPI直接シェアができないためクリップボードコピー
      navigator.clipboard.writeText(`${text}\n${shareUrl}`);
      showToast("和歌と言葉をクリップボードにコピーしました！Instagramでシェアしてください。");
    }
  };

  const currentUserAvatarObj = AVATARS.find(a => a.id === (user?.avatar || "genji"));

  return (
    <main className="min-h-screen flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-genji-gold via-genji-purple to-genji-gold opacity-80" />
      
      {/* ナビゲーションバー（右上ログイン・アバター） */}
      <div className="absolute top-6 right-6 z-30 flex items-center space-x-3">
        {user ? (
          <div className="flex items-center space-x-3 bg-white/60 backdrop-blur-sm px-4 py-2 rounded-full border border-genji-gold/40 shadow-md">
            {/* アバター画像 */}
            <button 
              onClick={() => setShowAvatarModal(true)}
              className="w-10 h-10 rounded-full border-2 border-genji-gold overflow-hidden transition-transform duration-200 hover:scale-105"
              title="アバターを変更"
            >
              <img 
                src={currentUserAvatarObj?.file} 
                alt={currentUserAvatarObj?.name} 
                className="w-full h-full object-cover" 
              />
            </button>
            <div className="text-right hidden sm:block">
              <p className="text-[10px] text-genji-ink/50 leading-none">ログイン中</p>
              <p className="text-xs font-bold text-genji-purple leading-tight truncate max-w-[150px]">{user.email}</p>
            </div>
            <button 
              onClick={handleLogout}
              className="p-1.5 hover:bg-genji-red/10 text-genji-red rounded-full transition-colors duration-200"
              title="ログアウト"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        ) : (
          <button 
            onClick={() => { resetAuthForm(); setAuthMode("login"); setShowAuthModal(true); }}
            className="flex items-center px-5 py-2.5 bg-gradient-to-r from-genji-purple to-genji-red text-white text-sm font-medium rounded-full shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-300"
          >
            <User className="w-4 h-4 mr-2" />
            雅なるログイン
          </button>
        )}
      </div>

      <div className="max-w-3xl w-full z-10">
        <header className="text-center mb-12">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1 }}
          >
            <h1 className="text-4xl sm:text-5xl font-bold text-genji-purple mb-4 tracking-widest drop-shadow-sm">
              源氏鏡
            </h1>
            <p className="text-genji-red text-lg font-medium tracking-widest mb-2">〜 千年共感エンジン 〜</p>
            <p className="text-genji-ink opacity-80 text-sm">
              千年前の雅な世界から、現代のあなたの悩みに寄り添います。
            </p>
          </motion.div>
        </header>

        {!result && !isLoading && (
          <motion.form 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-white/50 backdrop-blur-sm rounded-xl p-6 sm:p-8 shadow-xl border border-genji-gold/30"
            onSubmit={handleSubmit}
          >
            <label htmlFor="concern" className="block text-lg font-medium text-genji-purple mb-4 text-center">
              あなたの胸の内に秘めたお悩みをお聞かせください
            </label>
            <textarea
              id="concern"
              rows={5}
              className="w-full bg-white/70 border border-genji-gold/50 rounded-lg p-4 text-genji-ink focus:ring-2 focus:ring-genji-purple focus:border-transparent transition-all duration-300 resize-none outline-none"
              placeholder="例：最近、職場の同期が先に昇進して焦っている。しかも上司の態度が冷たくて孤独を感じる..."
              value={concern}
              onChange={(e) => setConcern(e.target.value)}
            />
            {error && (
              <p className="text-genji-red mt-2 text-sm text-center font-medium">{error}</p>
            )}
            <div className="mt-6 text-center">
              <button
                type="submit"
                disabled={!concern.trim()}
                className="inline-flex items-center px-8 py-3 bg-gradient-to-r from-genji-purple to-genji-red text-white font-medium rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ScrollText className="w-5 h-5 mr-2" />
                鏡に問う
              </button>
            </div>
          </motion.form>
        )}

        <AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-20"
            >
              <div className="relative w-24 h-24">
                <motion.div
                  className="absolute inset-0 border-4 border-genji-gold/30 rounded-full"
                />
                <motion.div
                  className="absolute inset-0 border-4 border-t-genji-purple rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                />
                <Sparkles className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-genji-gold w-8 h-8" />
              </div>
              <motion.p
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="mt-6 text-genji-purple font-medium tracking-widest text-lg"
              >
                千年先へ想いを馳せております...
              </motion.p>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {result && !isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-8"
            >
              {/* Refを付与した神託カード全体 */}
              <div 
                ref={cardRef}
                className="bg-[#f4e9d8] rounded-2xl overflow-hidden shadow-2xl border-2 border-genji-gold/50 p-1 sm:p-2"
                style={{ fontFamily: '"Hiragino Mincho ProN", "Yu Mincho", serif' }}
              >
                <div className="border border-genji-gold/30 rounded-xl overflow-hidden bg-white/60 backdrop-blur-md">
                  {/* Image Section */}
                  <div className="relative h-64 sm:h-80 w-full overflow-hidden border-b-4 border-genji-gold">
                    <img
                      src={result.image_url}
                      alt="源氏物語絵巻風画像"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                    <div className="absolute bottom-4 left-6">
                      <span className="px-4 py-1.5 bg-genji-red/90 text-white text-sm font-bold tracking-wider rounded-full shadow-lg backdrop-blur-sm border border-white/20">
                        {result.character}
                      </span>
                    </div>
                  </div>

                  {/* Content Section */}
                  <div className="p-6 sm:p-10 space-y-8 relative">
                    {/* Watermark/Decoration */}
                    <BookOpen className="absolute top-10 right-10 w-32 h-32 text-genji-gold/10 -rotate-12 pointer-events-none" />

                    {/* Message */}
                    <div className="relative z-10">
                      <h2 className="text-2xl font-bold text-genji-purple mb-4 border-b pb-2 border-genji-gold/30">
                        {result.character}からの言葉
                      </h2>
                      <p className="text-lg text-genji-ink leading-relaxed whitespace-pre-wrap font-serif">
                        {result.message}
                      </p>
                    </div>

                    {/* Waka */}
                    <div className="bg-gradient-to-br from-genji-gold/10 to-transparent p-6 rounded-xl border border-genji-gold/20 relative z-10">
                      <h3 className="text-lg font-medium text-genji-red mb-4 flex items-center">
                        <Sparkles className="w-5 h-5 mr-2" />
                        贈る和歌
                      </h3>
                      <div className="space-y-4">
                        <p className="text-xl sm:text-2xl font-serif text-genji-purple text-center tracking-widest leading-loose">
                          {result.waka}
                        </p>
                        <p className="text-sm text-genji-ink/80 text-center border-t border-genji-gold/30 pt-3 font-sans">
                          {result.waka_translation}
                        </p>
                      </div>
                    </div>

                    {/* Explanation */}
                    <div className="relative z-10">
                      <h3 className="text-md font-bold text-genji-purple/80 mb-2">
                        【背景解説】
                      </h3>
                      <p className="text-sm text-genji-ink/90 leading-relaxed bg-white/50 p-4 rounded-lg border border-white/50 shadow-sm font-sans">
                        {result.explanation}
                      </p>
                    </div>

                    {/* PDFダウンロードバー */}
                    <div className="border-t border-genji-gold/30 pt-6 flex justify-center font-sans">
                      <button
                        onClick={downloadPDF}
                        className="inline-flex items-center px-6 py-2 border border-genji-gold text-genji-purple hover:bg-genji-gold/10 font-bold rounded-full text-sm shadow-sm transition-all duration-300"
                      >
                        <ScrollText className="w-5 h-5 mr-2" />
                        神託札をPDFで全面保存
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="text-center">
                <button
                  onClick={() => setResult(null)}
                  className="px-8 py-3 border-2 border-genji-purple text-genji-purple rounded-full hover:bg-genji-purple hover:text-white shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-300 font-medium"
                >
                  新たなる悩みを問う
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* 雅なる神託札 (Card Collection History) */}
      {history.length > 0 && (
        <motion.section 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.6 }}
          className="max-w-5xl w-full z-10 mt-16 px-4 pb-12"
        >
          <div className="flex items-center justify-center space-x-3 mb-8">
            <History className="w-6 h-6 text-genji-purple" />
            <h2 className="text-2xl font-bold text-genji-purple tracking-widest font-serif border-b-2 border-genji-gold/45 pb-2">
              雅なる神託札コレクション
            </h2>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            {history.map((item) => (
              <motion.div
                key={item.id}
                whileHover={{ y: -6, scale: 1.02 }}
                onClick={() => handleLoadHistory(item)}
                className="bg-white/60 backdrop-blur-sm rounded-xl overflow-hidden shadow-lg hover:shadow-2xl border border-genji-gold/30 cursor-pointer flex flex-col transition-all duration-300 relative group"
              >
                {/* Delete Button */}
                <button
                  onClick={(e) => handleDeleteHistory(e, item.id)}
                  className="absolute top-3 right-3 p-2 bg-black/40 hover:bg-genji-red/90 text-white rounded-full transition-colors duration-200 z-20 opacity-0 group-hover:opacity-100 focus:opacity-100"
                  aria-label="この神託を破棄する"
                >
                  <Trash2 className="w-4 h-4" />
                </button>

                {/* Card Image */}
                <div className="relative h-40 w-full overflow-hidden border-b-2 border-genji-gold/20">
                  <img
                    src={item.image_url}
                    alt={item.character}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                  <div className="absolute bottom-3 left-4">
                    <span className="px-3 py-1 bg-genji-red/80 text-white text-xs font-bold rounded-full border border-white/10 shadow-sm">
                      {item.character}
                    </span>
                  </div>
                </div>

                {/* Card Info */}
                <div className="p-4 flex-1 flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <span className="text-[10px] text-genji-ink/50 block">
                      {item.timestamp}
                    </span>
                    <h3 className="text-sm font-bold text-genji-purple line-clamp-1 font-serif">
                      問い：{item.concern}
                    </h3>
                    <p className="text-xs text-genji-ink/80 line-clamp-3 leading-relaxed font-serif italic">
                      「{item.message}」
                    </p>
                  </div>
                  
                  {/* Small Waka Preview */}
                  <div className="bg-genji-gold/10 p-2 rounded border border-genji-gold/20 text-center mt-2">
                    <p className="text-xs font-serif text-genji-purple truncate">
                      {item.waka}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.section>
      )}

      {/* 1. 安全なる認証モーダル (Login / Register / Password Reset) */}
      <AnimatePresence>
        {showAuthModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => { setShowAuthModal(false); resetAuthForm(); }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            
            {/* Modal Container */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-[#f4e9d8] max-w-md w-full rounded-2xl overflow-hidden shadow-2xl border-2 border-genji-gold relative z-10 p-1"
            >
              <div className="border border-genji-gold/30 rounded-xl bg-white/70 backdrop-blur-md p-6 sm:p-8 space-y-6">
                
                {/* Header */}
                <div className="text-center space-y-2">
                  <h3 className="text-2xl font-bold text-genji-purple font-serif tracking-widest">
                    {authMode === "login" && "雅なるログイン"}
                    {authMode === "register" && "新たなる門人の登録"}
                    {authMode === "forgot" && "パスワード再設定の申請"}
                    {authMode === "reset" && "新パスワードの登録"}
                  </h3>
                  <p className="text-xs text-genji-ink/60">
                    {authMode === "forgot" ? "ご登録のメールアドレスを入力してください。" : "千年前の書物があなたの訪れをお待ちしております。"}
                  </p>
                </div>

                {/* Login tabs (Google vs Standard) */}
                {(authMode === "login" || authMode === "register") && (
                  <div className="flex bg-genji-gold/10 p-1 rounded-full border border-genji-gold/20">
                    <button
                      type="button"
                      onClick={() => { setIsGoogleLogin(false); setAuthError(""); }}
                      className={`flex-1 py-1.5 text-xs font-bold rounded-full transition-all duration-300 ${!isGoogleLogin ? "bg-genji-purple text-white shadow" : "text-genji-purple/70 hover:text-genji-purple"}`}
                    >
                      通常ログイン
                    </button>
                    <button
                      type="button"
                      onClick={() => { setIsGoogleLogin(true); setAuthError(""); }}
                      className={`flex-1 py-1.5 text-xs font-bold rounded-full transition-all duration-300 ${isGoogleLogin ? "bg-genji-purple text-white shadow" : "text-genji-purple/70 hover:text-genji-purple"}`}
                    >
                      Googleでログイン
                    </button>
                  </div>
                )}

                {/* Form */}
                <form onSubmit={handleAuthSubmit} className="space-y-4">
                  {/* Email */}
                  <div className="space-y-1">
                    <label className="text-xs font-bold text-genji-purple flex items-center">
                      <Mail className="w-3.5 h-3.5 mr-1" />
                      {isGoogleLogin ? "Google メールアドレス (@gmail.com)" : "メールアドレス"}
                    </label>
                    <input
                      type="email"
                      required
                      placeholder={isGoogleLogin ? "yourname@gmail.com" : "email@example.com"}
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      className="w-full bg-white/80 border border-genji-gold/50 rounded-lg p-2.5 text-sm text-genji-ink outline-none focus:ring-2 focus:ring-genji-purple"
                    />
                  </div>

                  {/* Password (except forgot mode) */}
                  {authMode !== "forgot" && (
                    <div className="space-y-1">
                      <label className="text-xs font-bold text-genji-purple flex items-center">
                        <Key className="w-3.5 h-3.5 mr-1" />
                        {authMode === "reset" ? "新しいパスワード" : "パスワード"}
                      </label>
                      <input
                        type="password"
                        required
                        minLength={6}
                        placeholder="6文字以上のパスワード"
                        value={passwordInput}
                        onChange={(e) => setPasswordInput(e.target.value)}
                        className="w-full bg-white/80 border border-genji-gold/50 rounded-lg p-2.5 text-sm text-genji-ink outline-none focus:ring-2 focus:ring-genji-purple"
                      />
                    </div>
                  )}

                  {/* Confirm Password (register and reset mode only) */}
                  {(authMode === "register" || authMode === "reset") && (
                    <div className="space-y-1">
                      <label className="text-xs font-bold text-genji-purple flex items-center">
                        <Key className="w-3.5 h-3.5 mr-1" />
                        確認用パスワード
                      </label>
                      <input
                        type="password"
                        required
                        placeholder="パスワードを再入力"
                        value={confirmPasswordInput}
                        onChange={(e) => setConfirmPasswordInput(e.target.value)}
                        className="w-full bg-white/80 border border-genji-gold/50 rounded-lg p-2.5 text-sm text-genji-ink outline-none focus:ring-2 focus:ring-genji-purple"
                      />
                    </div>
                  )}

                  {/* Reset Token Input (reset mode only) */}
                  {authMode === "reset" && (
                    <div className="space-y-1">
                      <label className="text-xs font-bold text-genji-purple flex items-center">
                        <Sparkles className="w-3.5 h-3.5 mr-1" />
                        リセットコード (6桁)
                      </label>
                      <input
                        type="text"
                        required
                        maxLength={6}
                        placeholder="コードを入力"
                        value={resetTokenInput}
                        onChange={(e) => setResetTokenInput(e.target.value)}
                        className="w-full bg-white/80 border border-genji-gold/50 rounded-lg p-2.5 text-sm text-genji-ink text-center tracking-widest font-bold outline-none focus:ring-2 focus:ring-genji-purple"
                      />
                    </div>
                  )}

                  {/* Security assurance info */}
                  <div className="p-3 bg-genji-gold/5 rounded-lg border border-genji-gold/10 flex items-start space-x-2 text-[10px] text-genji-ink/75 leading-relaxed">
                    <ShieldAlert className="w-4 h-4 text-genji-red flex-shrink-0 mt-0.5" />
                    <p>
                      <strong>【セキュリティ確保】</strong>入力されたパスワードは安全に暗号ハッシュ化(Bcrypt)されるため、開発者を含むいかなる第三者もパスワードを閲覧・解読することはできません。
                    </p>
                  </div>

                  {/* Demo/Helper info for developers to test forgotten password codes */}
                  {demoResetToken && (
                    <div className="p-3 bg-genji-red/5 text-genji-red rounded-lg border border-genji-red/10 text-xs font-bold text-center">
                      デモ用の再設定コード: <span className="underline tracking-widest">{demoResetToken}</span>
                    </div>
                  )}

                  {/* Error & Message */}
                  {authError && <p className="text-xs font-bold text-genji-red text-center">{authError}</p>}
                  {authMessage && <p className="text-xs font-bold text-genji-purple text-center">{authMessage}</p>}

                  {/* Submit Button */}
                  <button
                    type="submit"
                    className="w-full py-2.5 bg-gradient-to-r from-genji-purple to-genji-red text-white text-sm font-bold rounded-lg shadow-md hover:shadow-lg transition-all duration-300"
                  >
                    {authMode === "login" && (isGoogleLogin ? "Googleメールでログイン" : "ログイン")}
                    {authMode === "register" && "登録する"}
                    {authMode === "forgot" && "リセットコードを請求"}
                    {authMode === "reset" && "新パスワードに更新"}
                  </button>
                </form>

                {/* Switch Actions */}
                <div className="border-t border-genji-gold/20 pt-4 flex flex-col items-center space-y-2 text-xs">
                  {authMode === "login" && (
                    <>
                      <button 
                        type="button" 
                        onClick={() => { setAuthMode("register"); setAuthError(""); }}
                        className="text-genji-purple hover:underline"
                      >
                        新規ユーザー登録はこちら
                      </button>
                      {!isGoogleLogin && (
                        <button 
                          type="button" 
                          onClick={() => { setAuthMode("forgot"); setAuthError(""); }}
                          className="text-genji-red hover:underline"
                        >
                          パスワードをお忘れですか？
                        </button>
                      )}
                    </>
                  )}
                  {authMode === "register" && (
                    <button 
                      type="button" 
                      onClick={() => { setAuthMode("login"); setAuthError(""); }}
                      className="text-genji-purple hover:underline"
                    >
                      既に登録済みの方はログイン
                    </button>
                  )}
                  {(authMode === "forgot" || authMode === "reset") && (
                    <button 
                      type="button" 
                      onClick={() => { setAuthMode("login"); resetAuthForm(); }}
                      className="text-genji-purple hover:underline"
                    >
                      ログイン画面に戻る
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* 2. 雅なるアバター選択モーダル */}
      <AnimatePresence>
        {showAvatarModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowAvatarModal(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            
            {/* Modal Container */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-[#f4e9d8] max-w-lg w-full rounded-2xl overflow-hidden shadow-2xl border-2 border-genji-gold relative z-10 p-1"
            >
              <div className="border border-genji-gold/30 rounded-xl bg-white/70 backdrop-blur-md p-6 sm:p-8 space-y-6">
                <div className="text-center">
                  <h3 className="text-xl font-bold text-genji-purple font-serif tracking-widest">人物絵（アバター）の選択</h3>
                  <p className="text-xs text-genji-ink/60 mt-1">源氏物語の登場人物から、あなたを象徴する肖像をお選びください。</p>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  {AVATARS.map((avatar) => (
                    <button
                      key={avatar.id}
                      onClick={() => handleSelectAvatar(avatar.id)}
                      className={`p-3 rounded-xl border flex flex-col items-center space-y-2 transition-all duration-300 bg-white/60 hover:bg-genji-gold/10 hover:border-genji-gold ${user?.avatar === avatar.id ? "border-2 border-genji-purple ring-2 ring-genji-purple/20 bg-genji-purple/5" : "border-genji-gold/20"}`}
                    >
                      <div className="w-16 h-16 rounded-full border border-genji-gold/50 overflow-hidden shadow-sm">
                        <img src={avatar.file} alt={avatar.name} className="w-full h-full object-cover" />
                      </div>
                      <span className="text-xs font-bold text-genji-purple font-serif">{avatar.name}</span>
                    </button>
                  ))}
                </div>
                
                <div className="text-center">
                  <button 
                    onClick={() => setShowAvatarModal(false)}
                    className="px-6 py-2 border border-genji-purple text-genji-purple rounded-full text-xs hover:bg-genji-purple hover:text-white transition-colors duration-200"
                  >
                    閉じる
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* 3. トースト表示 (Toast alerts) */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 right-6 z-50 bg-genji-purple/90 backdrop-blur-sm text-[#f4e9d8] px-5 py-3 rounded-xl shadow-2xl border border-genji-gold/50 text-xs font-bold flex items-center space-x-2"
          >
            <Sparkles className="w-4 h-4 text-genji-gold animate-pulse" />
            <span>{toast}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
