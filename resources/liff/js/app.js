document.addEventListener('DOMContentLoaded', function() {
  // 初始化頁面事件監聽
  initEventListeners();
});

// 初始化事件監聽器
function initEventListeners() {
  // 返回按鈕
  const backButton = document.getElementById('backButton');
  if (backButton) {
    backButton.addEventListener('click', function() {
      liff.closeWindow();
    });
  }
  
  // 菜單按鈕
  const menuButton = document.getElementById('menuButton');
  if (menuButton) {
    menuButton.addEventListener('click', function() {
      alert('功能選單即將推出');
    });
  }
  
  // 底部導航項目
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach((item, index) => {
    item.addEventListener('click', function() {
      // 移除所有活躍狀態
      navItems.forEach(navItem => navItem.classList.remove('active'));
      
      // 添加當前活躍狀態
      item.classList.add('active');
      
      // 根據索引切換頁面
      switch(index) {
        case 0: // 首頁
          window.location.href = '?feature=dashboard';
          break;
        case 1: // 學習
          window.location.href = '?feature=learning';
          break;
        case 2: // 卡片
          window.location.href = '?feature=cards';
          break;
        case 3: // 報告
          window.location.href = '?feature=report';
          break;
      }
    });
  });
  
  // 卡片點擊事件
  const learningCards = document.querySelectorAll('.learning-card');
  learningCards.forEach(card => {
    card.addEventListener('click', function(e) {
      // 如果點擊的是卡片而不是按鈕
      if (!e.target.classList.contains('action-button')) {
        const title = card.querySelector('.card-title').textContent;
        alert(`即將打開「${title}」學習內容`);
      }
    });
  });
  
  // 按鈕點擊事件
  const actionButtons = document.querySelectorAll('.action-button');
  actionButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.stopPropagation(); // 阻止冒泡到卡片
      
      const parentCard = button.closest('.learning-card');
      const title = parentCard.querySelector('.card-title').textContent;
      const action = button.textContent;
      
      if (action.includes('繼續學習')) {
        alert(`開始學習「${title}」`);
      } else if (action.includes('查看筆記')) {
        alert(`查看「${title}」的筆記`);
      }
    });
  });
}

// 獲取學習數據 (示例函數)
function fetchLearningData() {
  // 這裡模擬與後端 API 通信
  return new Promise((resolve, reject) => {
    // 模擬網絡延遲
    setTimeout(() => {
      // 假數據
      const data = {
        topics: 12,
        totalHours: 36.5,
        reviewRate: 86,
        achievements: 8,
        todayTasks: [
          {
            title: '熱力學基礎',
            progress: 75,
            description: '了解熱力學第一定律和第二定律的核心概念與應用'
          },
          {
            title: '記憶術訓練',
            progress: 45,
            description: '記憶宮殿法和間隔重複系統的實際練習'
          }
        ]
      };
      
      resolve(data);
    }, 500);
  });
}

// 分享功能
function shareProgress() {
  if (liff.isApiAvailable('shareTargetPicker')) {
    liff.shareTargetPicker([
      {
        type: 'text',
        text: '我今天已經完成了75%的學習進度！一起學習進步吧！'
      }
    ])
    .then(function(res) {
      if (res) {
        // 分享成功
        alert('分享成功！');
      } else {
        // 用戶取消分享
        console.log('用戶取消分享');
      }
    })
    .catch(function(error) {
      console.log('分享失敗', error);
    });
  } else {
    alert('此裝置不支援分享功能');
  }
} 