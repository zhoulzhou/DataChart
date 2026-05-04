<script setup>
defineProps({
  cardsData: {
    type: Object,
    default: () => ({})
  }
})

function fmt(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const items = [
  { key: 'revenue', label: '营业收入', color: '#4361ee' },
  { key: 'operating_cost', label: '营业成本', color: '#f72585' },
  { key: 'gross_profit', label: '毛利', color: '#2ec4b6' },
  { key: 'net_profit', label: '净利', color: '#7209b7' },
  { key: 'operating_cash_flow', label: '经营现金流净额', color: '#f8961e' },
  { key: 'inventory', label: '存货', color: '#4cc9f0' },
  { key: 'accounts_receivable', label: '应收账款', color: '#e63946' },
  { key: 'cash_total', label: '现金总额', color: '#06d6a0' },
  { key: 'contract_liabilities', label: '合同负债', color: '#ffd166' }
]
</script>

<template>
  <div class="kpi-grid">
    <div v-for="item in items" :key="item.key" class="kpi-card">
      <div class="kpi-label">{{ item.label }}</div>
      <div class="kpi-value" :style="{ color: item.color }">{{ fmt(cardsData[item.key]) }}</div>
    </div>
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 18px 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  border-top: 3px solid #e0e0e0;
}
.kpi-label {
  font-size: 13px;
  color: #888;
  margin-bottom: 8px;
}
.kpi-value {
  font-size: 20px;
  font-weight: 700;
}

@media (max-width: 992px) {
  .kpi-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 576px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .kpi-value { font-size: 17px; }
}
</style>
