const categoryRules: [RegExp, string][] = [
  [/(silpo|carrefour|auchan|metro|atb|novus|grocery|groceries|supermarket|bakery|deli)/i, 'Food & Dining'],
  [/(kfc|mcdonald|burger|pizza|restaurant|cafe|diner|dining|bbq|grill)/i, 'Food & Dining'],
  [/(shell|wog|okko|esso|bp|gas station|gasoline|petrol|diesel|fuel)/i, 'Transportation'],
  [/(uber|taxi|lyft|metro|bus|train|subway|parking|toll|car rental|rental car)/i, 'Transportation'],
  [/(vodafone|kyivstar|lifecell|internet|mobile|phone|telecom|electric|water|gas bill|utility|utilities|power)/i, 'Utilities'],
  [/(apteka|pharmacy|medicine|medication|drugs|prescription|doctor|dental|hospital|clinic|gym|fitness|health|vitamin)/i, 'Healthcare'],
  [/(rozetka|amazon|ebay|aliexpress|shopping|mall|clothing|apparel|shoes|electronics|cosmetic|beauty|jewelry)/i, 'Shopping'],
  [/(book|course|tutorial|class|training|education|university|school|tuition)/i, 'Education'],
  [/(subscription|subscriptions|netflix|spotify)/i, 'Subscriptions'],
  [/(movie|cinema|theater|concert|amusement|park|game|gaming|entertainment|flight|flights|airline|airbnb|hotel|motel|travel|vacation|trip|tour|resort)/i, 'Entertainment'],
  [/(apartment|rent|mortgage|housing|lease|property|landlord)/i, 'Housing'],
  [/(insurance|insure)/i, 'Insurance'],
  [/(salary|payroll|wage|income)/i, 'Salary'],
  [/(freelance|contract|gig)/i, 'Freelance'],
  [/(dividend|stock|investment|interest|return)/i, 'Investment'],
]

export function categorizeByKeywords(rawText: string): string | null {
  for (const [pattern, category] of categoryRules) {
    if (pattern.test(rawText)) return category
  }
  return null
}
