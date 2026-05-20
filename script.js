const liveNumber = document.querySelector(".hero-stats span:first-child strong");
const matchNumber = document.querySelector(".hero-stats span:nth-child(2) strong");
const notification = document.querySelector(".icon-button");

let liveCount = 12482;
let matchCount = 3914;
let noticeCount = 7;

function formatNumber(value) {
  return new Intl.NumberFormat("ko-KR").format(value);
}

setInterval(() => {
  liveCount += Math.floor(Math.random() * 9) + 2;
  matchCount += Math.floor(Math.random() * 4) + 1;

  liveNumber.textContent = formatNumber(liveCount);
  matchNumber.textContent = formatNumber(matchCount);
}, 2600);

setInterval(() => {
  noticeCount = noticeCount >= 19 ? 7 : noticeCount + 1;
  notification.textContent = noticeCount;
}, 5200);

document.querySelectorAll(".match-row button").forEach((button) => {
  button.addEventListener("click", () => {
    button.textContent = "전송됨";
    button.disabled = true;
  });
});
