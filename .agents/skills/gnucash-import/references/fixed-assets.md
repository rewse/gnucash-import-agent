# Fixed assets

Apply these rules to assets held for years rather than consumed. All amounts are dummy values.

## Capitalization

Capitalize a purchase only when its amount would distort the payment month, a resale market provides a current value, and tracking the decline is useful. Capitalize real estate and cars. Expense computers, appliances, and home equipment regardless of price to preserve comparability with this book's history.

The JPY 100,000, 200,000, and 300,000 thresholds are business tax rules for depreciable assets. They do not apply while the book has no business or rental income. Ask a tax professional if the asset later gains business use.

## Acquisition cost

Record the item, consumption tax, delivered accessories, registration, and paperwork in `{asset}:Cost`. Registration taxes and paperwork may be expensed under another policy, but this book capitalizes them so the balance ties to the invoice.

Record period-based insurance in `Expenses:Insurances:Property Insurances`. Record refundable deposits in a sibling account such as `{asset}:Recycling Deposit`. Set `Cost` at acquisition and do not change it later.

## Valuation

Track market adjustments in the sibling `{asset}:Unrealized Gain` account. Do not use depreciation schedules for book valuation.

```text
{asset}:Cost                3,000,000
{asset}:Unrealized Gain      -400,000
                            ---------
carrying value              2,600,000
```

Use `Income:Real Estate Income:Unrealized Gains` as the counter account for real estate and `Income:Unrealized Gains` for other assets. When a current value is available, set the cumulative `Unrealized Gain` balance to `market value - Cost`; do not add the full adjustment again. Revaluation is usually performed twice a year.

```text
Assets:Fixed Assets:{asset}:Unrealized Gain    -400,000
Income:Unrealized Gains                         400,000
```

## Disposal

### Personal-use vehicle

Revalue the vehicle to the agreed sale price, then remove its `Cost` and `Unrealized Gain` balances. Carrying value then equals the proceeds, so do not create a realized gain or loss. Gains on a personal-use vehicle are generally outside Japanese income tax. Clear a refundable deposit separately when the buyer reimburses it or scrapping returns it.

```text
Assets:JPY - Current Assets:Banks:{bank}       2,600,000
Assets:Fixed Assets:{asset}:Cost              -3,000,000
Assets:Fixed Assets:{asset}:Unrealized Gain      400,000
```

### Real estate

Reverse the accumulated unrealized gain through `Income:Real Estate Income:Unrealized Gains`. Record the full `sale price - Cost` difference in `Income:Real Estate Income:Realized Gains`.

```text
Assets:JPY - Current Assets:Banks:{bank}                   60,000,000
Assets:Fixed Assets:{property}:Cost                       -20,000,000
Assets:Fixed Assets:{property}:Unrealized Gain            -35,000,000
Income:Real Estate Income:Unrealized Gains                 35,000,000
Income:Real Estate Income:Realized Gains                  -40,000,000
```

Record agent commission, stamp duty, registration, and other selling costs separately as sale expenses. Do not use the vehicle treatment for real estate or revalue real estate to the sale price before applying this treatment.

Book `Cost` is not the tax acquisition cost when building depreciation or a land-and-structure allocation applies. Treat `Realized Gains` as a starting point and ask a tax professional to calculate the filing amount.
