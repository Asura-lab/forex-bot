# Ашигтай стратеги хайсан локал туршилт

2026-11-05. **Зорилго нь ашигтай стратеги олох; энэ удаагийн шалгалтаар сонгож ажиллуулах шаардлага хангасан хувилбар олдоогүй.** Алдагдлыг багасгасныг ашигтай болсонтой адилтгаагүй. Код, бүх шалгасан хувилбар, эерэг болон сөрөг үр дүнг хадгалсан.

## Бодитоор нэмсэн боломж

- M15 өгөгдлөөс бүрэн H1/H4 лаа үүсгэнэ. Нэг дутуу M15 лаатай том лааг ашиглахгүй.
- Дохио тухайн том лаа хаагдсаны дараах M15 open-д л боломжтой болно. Зах зээл тасарсан үед хуучин дохиог хойшлуулж оруулахгүй.
- Орох/гарах, stop/target, gap, equity хамгаалалтыг M15 OHLC дээр тооцсон хэвээр. Том лааны бүх high/low-г entry-ээс өмнө мэддэг мэт ашиглаагүй.
- Calendar carry зардал нэмсэн: base $10/lot/day, stress $20/lot/day, хоёр чиглэлд зардал гэж тооцно. Weekend-ийн алгассан өдрүүдийг оруулна. Энэ нь тухайн брокерийн түүхэн swap биш, болгоомжтой таамаглал.
- Lot sizing-д holding хугацааны carry reserve нэмсэн. Default carry=0 болон default baseline дохио хэвээр тул өмнөх туршилтуудын зан төлөвийг өөрчлөөгүй.

Шинэ код: [стратегийн сан](../forexbot/strategies.py), [хайлт/сонголт/шалгалт](../forexbot/discovery.py), [гүйцэтгэлийн цөм](../forexbot/research.py).

## Шалгасан тогтсон хувилбарууд

[Төлөвлөгөөг](superpowers/plans/2026-11-05-strategy-discovery.md) дүн гарахаас өмнө хадгалсан. Channel/ATR/stop/target-ийг validation харсны дараа тохируулаагүй.

| Нэр | Логик | Stop / target | Арилжааны эрсдэлийн төсөв |
| --- | --- | --- | --- |
| h1-breakout20 | Өмнөх 20 H1 лааны түвшнийг давсан close | 2 / 4 ATR | 0.25% |
| h1-breakout55 | Өмнөх 55 H1 лаа | 2 / 4 ATR | 0.25% |
| h4-breakout20 | Өмнөх 20 H4 лаа | 1.5 / 3 ATR | 0.25% |
| h1-pullback | SMA20-ийг трендийн чигт буцаж давсан; SMA50/200 тренд | 2 / 3 ATR | 0.25% |
| h4-pullback | SMA20 буцаж давсан; SMA50/100 тренд | 1.5 / 3 ATR | 0.25% |
| h1-reentry | 20 лааны 2σ зурвас руу эргэн орсон; SMA100 slope range filter | 2 / 2 ATR | 0.25% |
| h4-reentry | Ижил re-entry, H4 | 1.5 / 2 ATR | 0.25% |
| m15-reentry | Ижил re-entry, M15 | 2 / 2 ATR | 0.25% |

ATR14 нь энгийн mean true range. Нэг position, $1,000 equity, 100:1 modeled leverage, 10% дотоод trailing halt, execution-cost/stop gate .20 хэвээр. Position хэмжээг broker-ийн min/step lot-д доош тоймлоно; төсөвт хүрэхгүй min lot-ыг хүчээр авахгүй.

## Өгөгдөл ба сонголт

Нийт 70,370 лаа:

1. Эхний **34,481** лаа: calibration. Дөрвөн цагийн дараалсан тусдаа дансаар бүх candidate-ийг харьцуулсан. Дор хаяж 30 арилжаатай candidate-уудаас pooled net profit factor, дараа нь net P/L-ээр нэгийг сонгосон.
2. Дараагийн **14,778** лаа: зөвхөн calibration-ийн сонгогдсон нэг candidate-д validation. Base/stress хоёул эерэг net, PF>1, дор хаяж 20 арилжаа шаардана.
3. Үлдсэн **21,111** лаа: calibration болон validation хоёрын base/stress шалгуур давсан үед л нэг historical check хийх нөхцөлтэй. **Энэ удаа шалгуур даваагүй тул уншиж performance тооцоогүй.**

Эдгээр түүхэн үнийн хэсгүүд өмнөх baseline/cost-filter судалгаанд ашиглагдсан тул цоо шинэ, урьд нь огт хараагүй holdout гэж нэрлээгүй. Олон candidate сонгосон bias мөн хэвээр. Neural-network эсвэл supervised-model сургалт энэ шатанд хийгээгүй; дүрэмд суурилсан стратегийн bounded search хийсэн.

## Эхний batch: 0.25% risk

| Candidate | Calibration арилжаа | Calibration net, USD | Net PF |
| --- | ---: | ---: | ---: |
| h1-breakout20 | 79 | −21.80 | 0.763 |
| h1-breakout55 | 36 | −24.15 | 0.483 |
| h4-breakout20 | 0 | 0 | — |
| h1-pullback | 59 | −28.84 | 0.567 |
| h4-pullback | 0 | 0 | — |
| h1-reentry | 101 | −58.96 | 0.496 |
| h4-reentry | 0 | 0 | — |
| m15-reentry | 367 | −61.92 | 0.808 |

Calibration-ийн USD дүн нь **дөрвөн шинэ $1,000 дансны P/L-ийн нийлбэр**, нэг тасралтгүй дансны өгөөж биш. M15 re-entry нь алдагдалтай хувилбаруудын дотроос өндөр PF-тэй байсан ч validation-д 165 арилжаа, −$62.35 / −6.235%, PF0.622 гарсан. Stress үед executable арилжаа0; ийм no-trade үр дүнг ашигтай гэж үзээгүй.

## H4 яагаад арилжаагүй байсан бэ?

0.25% risk нь $1,000 дансанд $2.50. H4 дохио байсан боловч broker-ийн хамгийн бага0.01 lot, том stop ба carry reserve-д энэ төсөв хүрэхгүй байв. Calibration signal220/105/100 ширхэг; modeled min-lot risk-ийн медиан0.460% /0.482% /0.433% байсан.

Үүнийг стратегийн бодит P/L гэж үзээгүй. Үр дүн харахаас өмнө төлөвлөгөөнд **тусдаа H4-only 1% risk feasibility batch** нэмж тэмдэглэсэн. Бусад дүрэм, stop/target, costs, 10% account halt-ыг өөрчлөөгүй. Энэ нь бага эрсдэлтэй эхний batch-ийг дарж солих эсвэл profit-ийг хэмжээ өсгөж сайжруулсан мэт тайлбарлах үйлдэл биш.

| H4 candidate, 1% cap | Calibration арилжаа | Дөрвөн дансны net USD | PF |
| --- | ---: | ---: | ---: |
| breakout20 | 106 | −202.29 | 0.566 |
| pullback | 68 | −70.75 | 0.750 |
| reentry | 93 | **+12.24** | **1.039** |

H4 re-entry calibration дээр эерэг гарсан. Гэвч validation:

| Нөхцөл | Арилжаа | Net USD | Нэг дансны өгөөж | Net PF | Modeled max DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base | 45 | −71.02 | −7.102% | 0.612 | 9.450% |
| Stress | 45 | −55.49 | −5.549% | 0.649 | 7.883% |

Stress бага алдагдсан нь өндөр зардал ашигтай гэсэн үг биш. Илүү өндөр reserve/fees нь lot хэмжээг бууруулдаг; заримдаа ижил тооны арилжаанд exposure өөр болдог. Нэрлэсэн P/L-ийг ижил хэмжээний trade-by-trade cost sensitivity гэж ойлгохгүй.

**Шийдвэр:** calibration-ийн +$12.24-ийг ашигтай ботын нотолгоо гэж сурталчлахгүй. Validation-д давтагдаагүй тул candidate-ийг хэрэгжүүлж ажиллуулах шалгуур давсангүй. Legacy period-ийн шалгалтыг нээгээгүй, шинэ order executor/серверийн байршуулалт хийгээгүй.

## Шалгалт ба дахин ажиллуулах

38 автомат тест давсан. Тусдаа code review ноцтой асуудал олоогүй. Pullback/re-entry-ийн future-independence тестэд үнэхээр дохио үүсгэдэг fixture ашиглаж, хоосон map-уудыг хооронд нь харьцуулсан төдий шалгалт болоогүйг нягталсан. Funding/weekend deduction, net-P/L reconciliation, minimum sample ба стрессийн алдагдалтай үр дүнг reject хийх gate-ийг мөн шалгасан.

```powershell
python -m unittest discover -s tests -v
python -m forexbot.discovery data/xmglobal-eurusd-m15-2026-11-05/bars.csv --config data/xmglobal-eurusd-m15-2026-11-05/config.json --output artifacts/new-bounded-run
python -m forexbot.discovery data/xmglobal-eurusd-m15-2026-11-05/bars.csv --config data/xmglobal-eurusd-m15-2026-11-05/config.json --risk-fraction .01 --timeframe-seconds 14400 --output artifacts/new-h4-feasibility-run
```

Review-ийн дараах эцсийн source-оор ижил параметртэй гүйлтүүдийг давтан хийсэн; параметр хайж өөрчилсөнгүй. [8 candidate-ийн тайлан](../artifacts/discovery-2026-11-05/bounded-v1-verified/summary.json), [H4 feasibility тайлан](../artifacts/discovery-2026-11-05/h4-feasibility-1pct-verified/summary.json), [verification/source hash](../artifacts/discovery-2026-11-05/verification.json). Анхны гүйлтүүдийг тусдаа archival хавтаст үлдээсэн.

Бүх гүйлт локал, захиалгагүй. Native shadow EA өмнөх baseline хэвээр. Prepared signal map болон шинэ стратегиудыг native EA-д портлоогүй. OHLC intrabar path, synthetic carry, lagged spread, батлагдаагүй fills болон өмнөх data exposure-ийн хязгааруудыг арилгаагүй; бодит ирээдүйн ашиг, тэмцээнд түрүүлэхийг батлаагүй.
