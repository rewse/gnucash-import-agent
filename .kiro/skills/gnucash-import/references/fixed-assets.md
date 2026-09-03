# Fixed Assets

How this book records assets that are held for years rather than consumed. All amounts below are dummy values.

## When to capitalize

Capitalize only when all three hold:

1. The amount would distort the month it was paid in
2. There is a resale market, so a current value can be looked up
3. Seeing the value decline is worth the effort of tracking it

Real estate and cars qualify. Computers, appliances, and home equipment do not, and they go straight to expense no matter the price. This book has expensed single purchases well above JPY 500,000, so capitalizing a laptop now would break comparability with that history.

The JPY 100,000 / 200,000 / 300,000 thresholds are business tax rules for depreciable assets. They have no effect on a book with no business or rental income. If an asset later gains business use, those thresholds start to matter and a tax professional should confirm the treatment.

## Acquisition cost

Goes into `{asset}:Cost`:

- The item itself, including consumption tax
- Accessories delivered with it
- Registration and paperwork fees

Kept out of `Cost`:

- Insurance premiums, which cover a period rather than the acquisition. Book them to `Expenses:Insurances:Property Insurances`
- Refundable deposits, which are recovered later. Give them their own sibling account, for example `{asset}:Recycling Deposit`

Registration taxes and paperwork fees may be expensed instead of capitalized. This book capitalizes them so that `Cost` ties to the invoice total in two or three subtractions, which makes the figure auditable years later.

`Cost` is set once at acquisition and never touched again.

## Market valuation

Both fixed assets carry a sibling `Unrealized Gain` account that adjusts the carrying value to market. Depreciation schedules are not used, because a formula drifts from what the asset would actually fetch, and the tax rates that drive those formulas mean nothing in a personal book.

```
{asset}:Cost                3,000,000   fixed at acquisition
{asset}:Unrealized Gain      -400,000   adjusted to market
                            ---------
carrying value              2,600,000
```

Counter accounts differ by asset class:

| Asset | Counter account |
|-------|-----------------|
| Real estate | `Income:Real Estate Income:Unrealized Gains` |
| Everything else | `Income:Unrealized Gains` |

Revalue when a current figure is available, twice a year in practice. The `Unrealized Gain` balance is cumulative, so each entry moves it to `market value - Cost` rather than adding a fresh delta. Revaluing a car for the first time after delivery shows a large drop, because a new vehicle loses value the moment it is registered.

```
Assets:Fixed Assets:{asset}:Unrealized Gain    -400,000
Income:Unrealized Gains                         400,000
```

## Disposal

Two variants, and which one applies depends on whether the realized figure has a use outside the book.

### Personal-use vehicle

Revalue to the agreed sale price first, then remove the asset. Carrying value equals the proceeds, so no realized gain or loss arises and no realized-gain account is needed. Gains on a personal-use vehicle are generally outside income tax in Japan, so the figure would have no reader.

```
Assets:JPY - Current Assets:Banks:{bank}       2,600,000
Assets:Fixed Assets:{asset}:Cost              -3,000,000
Assets:Fixed Assets:{asset}:Unrealized Gain      400,000
```

A refundable deposit clears separately, either reimbursed by the buyer or refunded on scrapping.

### Real estate

Keep the realized figure, because `sale price - Cost` is where a capital gains computation starts. Reverse the whole accumulated `Unrealized Gain` back through its counter account and book the full difference to `Income:Real Estate Income:Realized Gains`.

```
Assets:JPY - Current Assets:Banks:{bank}                   60,000,000
Assets:Fixed Assets:{property}:Cost                       -20,000,000
Assets:Fixed Assets:{property}:Unrealized Gain            -35,000,000
Income:Real Estate Income:Unrealized Gains                 35,000,000
Income:Real Estate Income:Realized Gains                  -40,000,000
```

Reversing the accumulated gain prevents double reporting. The disposal year shows only the movement since the last revaluation, JPY 5,000,000 in the example, while `Realized Gains` carries the whole JPY 40,000,000.

Selling costs such as agent commission, stamp duty, and registration are expenses of the sale rather than valuation, so record them separately.

Do not use this variant for an asset revalued to its sale price, and do not use the vehicle variant for real estate: the residual would be the movement since the last revaluation, which tells a tax return nothing.

The book `Cost` is unlikely to equal the acquisition cost a tax return wants, since a building's figure is reduced by accumulated depreciation and land must be separated from the structure. Treat `Realized Gains` as a starting point and have a tax professional compute the filing figure.
