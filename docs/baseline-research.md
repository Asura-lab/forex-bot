# Эхний стратеги ба локал туршилт

2026-11-05. Судалгааны эхний суурь хувилбар бэлэн. **Энэ стратегийн бодит түүхэн өгөгдлийн эхний үр дүн алдагдалтай.** Серверт шинэ стратеги байрлуулаагүй; Oracle-ийн өмнөх runtime probe хэвээр. Тэмцээний MT5 холболтын асуудал тусдаа нээлттэй.

Дараагийн локал шинэчлэл: [давтагдах 7/14 хоногийн шат ба optional зардлын шүүлтүүр](recurring-rounds.md). Энэ хуудсан дахь 19 тест, source hash болон үр дүн нь эхний хувилбарын түүхэн баримт; шинэ хувилбар 28 тесттэй. Эхний artifact-уудыг дарж шинэчлээгүй.

## Нэг тогтсон эхний стратеги

- EURUSD, M15, USD демо данс.
- Хаагдсан лааны close өмнөх 20 лааны high-аас өндөр бол buy дохио; өмнөх 20 low-оос доогуур бол sell. Тэнцүү үед дохиогүй. Дохионы лаа өөрийн channel-д орохгүй.
- ATR нь сүүлийн 14 true range-ийн **энгийн дундаж**; Wilder ATR биш. Stop = 2 ATR, target = 3 ATR. Хугацаагаар хамгийн ихдээ 96 лаа барина.
- Дохионы дараагийн лааны open дээр орох загвар. Нэг л position. Арилжаа бүрийн төсөв equity-ийн 0.25%; хамгийн бага lot-ыг хүчээр авахгүй. Загварын хөшүүрэг 100:1, margin-д equity-ийн дээд тал нь 20% ашиглана.
- Оргил equity-гээс 10% унавал дотоод хамгаалалт тухайн туршилтыг зогсооно; дахин өссөн ч автоматаар үргэлжлүүлэхгүй. Тэмцээний 20%-ийн босгоос тусдаа. Gap болон гарах зардлаас загварын 10% босгыг бага зэрэг давах боломжтой.

Эдгээр параметрийг өгөгдлийн үр дүнг харахаас өмнө суурь жишээ болгон сонгосон. Оновчлол, нейрон сүлжээний сургалт хийгээгүй. Энэ хувилбарын зорилго нь дараагийн стратегийн үр дүнг хэмжих тогтмол харьцуулалттай болох.

## Бодитоор хийсэн туршилт

Таны өмнө зөвшөөрсөн XMGlobal демо холболтоор MT5-ийн read-only API ашиглан **70,370 M15 лаа** экспортолсон. Broker-ийн EURUSD contract size 100,000, point 0.00001, min/step lot 0.01, max lot 50 гэж уншигдсан. Дансны USD/demo төлөвийг шалгасан. Нууц үгийг өмнөх хувийн INI файлаас уншсан; репозитор, тайлан, командын аргумент болон stdout-д оруулаагүй.

Хүссэн интервал: 2024-01-01–2026-11-01 (end exclusive). Бодит эхний/сүүлийн epoch-ийг UTC хэлбэрээр дүрслэхэд 2024-01-02 00:00–2026-10-30 22:45. Raw MT5 epoch-ийг хадгалсан; порталын тэмцээний timezone гэж тайлбарлаагүй.

Үнийн CSV, symbol config, metadata: локал `data/xmglobal-eurusd-m15-2026-11-05/`. Том өгөгдөл болон виртуал орчин `.gitignore`-д орсон. Өгөгдлийн SHA-256: `c43c4662415d6a01b5d4bc60dc1bdb2b89535864dddca43882b52f063edc7aa9`.

Өгөгдлийн чанарын ажиглалт: zero spread-тай лаа 0, median spread 18 point, 95-р percentile 20 point, хамгийн өндөр 144 point. 151 залгаа интервал 15 минутаас урт; бүгд 900 секундын үржвэр. Weekend/амралт болон бусад history gap-ийг нөхөж зохиомол лаа үүсгээгүй; урт gap бүрийн шалтгааныг тусад нь ангилаагүй.

Өгөгдлийг цагийн дарааллаар 70/30 хуваасан. Хоёр хэсэг тус бүр шинэ $1,000 загварын дансаар эхэлнэ. Үнэлгээний өмнөх 21 лааг зөвхөн indicator warmup-д ашигласан; түүн дээр үнэлгээний арилжаа нээгээгүй. Параметрийг хэсгүүдийн хооронд өөрчлөөгүй.

| Үзүүлэлт | Эхний 70% | Дараагийн 30% үнэлгээ |
| --- | ---: | ---: |
| Дуусах equity | $903.63 | $900.49 |
| Өгөөж, загварын зардлын дараа | −9.64% | −9.95% |
| Арилжааны тоо | 190 | 243 |
| Ашигтай арилжааны хувь | 32.11% | 33.33% |
| Profit factor | 0.586 | 0.657 |
| Загварын дээд уналт | 10.03% | 10.01% |
| Дотоод хамгаалалт зогсоосон | Тийм | Тийм |

Үнэлгээний хэсэг 2025-12-24 02:15-аас эхэлсэн. Хамгаалалт 2026-03-30 орчим зогсоосны дараа 2026-10-30 хүртэл шинэ арилжаа нээгээгүй; сүүлийн сарын бүх хугацаанд идэвхтэй арилжсан гэсэн тайлбар биш. Эхний хэсэг ч 2024-03-04 орчим зогссон. Эдгээр нь данс reset хийхгүй урт туршилтууд; долоо хоног/хоёр долоо хоногийн бодит тэмцээний шат бүрийн үр дүн биш.

Шимтгэл хасахаас өмнөх, спред ба slippage багтсан P/L ч сөрөг: эхний хэсэг −$72.15, үнэлгээ −$74.80. Алдагдлыг зөвхөн шимтгэлтэй холбон тайлбарлах үндэслэлгүй. Энэ стратегийг орлого олно гэж үзэж байрлуулахгүй.

Эхний гүйлтэд тухайн бүрэн лааны spread-ийг open-д мэдэгдсэн мэт ашиглаж байсныг review үеэр зассан. Одоо өмнөх хаагдсан лааны spread-ээр дараагийн лааны спредийг загварчилна. Засварын өмнөх `first-evaluation` архивыг түүх болгон үлдээсэн; **ашиглах үр дүн нь [final-evaluation](../artifacts/baseline-2026-11-05/final-evaluation/summary.json)**. Дараагийн хувилбарыг энэ үнэлгээний хэсэгт тааруулбал түүнийг шинэ, хараагүй holdout гэж дахин нэрлэхгүй; шинэ хугацаа эсвэл урьдчилан тогтоосон walk-forward үнэлгээ хэрэгтэй.

## Хэрэгжүүлэлт

- [Python судалгааны цөм](../forexbot/research.py): дохио, хэмжээ, trailing хамгаалалт, account-key-ээр тусгаарласан peak/halt хадгалалт, OHLC симуляц.
- [CLI](../forexbot/__main__.py): CSV шалгалт, тогтмол параметртэй chronological split, JSON / trade / equity тайлан.
- [MT5 экспорт](../tools/export_mt5.py): зөвхөн үнийн түүх, symbol/account specification уншина. Order API дуудлагагүй; real/contest эсвэл USD биш дансыг зөвшөөрөхгүй.
- [Native shadow EA](../strategy/mt5/BaselineShadow.mq5): ижил closed-bar channel/mean-TR дохио, equity heartbeat, account/server-ээр тусгаарласан peak/halt. **Захиалга өгөх, position хаах функцгүй.** MetaEditor-оор 0 errors / 0 warnings compile хийсэн; терминалд attach хийж forward ажиллагааг хараахан хэмжээгүй. Python ба MQL5-ийн дохионы tick replay parity мөн хараахан шалгаагүй.

Shadow EA зөвхөн демо/USD/EURUSD дээр initialize хийнэ. Account солигдвол дохиог зогсооно. Нэг MT5 terminal дотор account/server тус бүрийн global state ашиглана. Terminal globals 4 долоо хоног ашиглаагүй бол устдаг; өмнөх оргилыг бүх түүхээс сэргээх шийдэл биш. Өөр терминалд state автоматаар дамжихгүй. Тиймээс энэ нь тэмцээний гүйцэтгэгчийн бүрэн хамгаалалт хараахан биш.

19 автомат шалгалт давсан: дохио/ATR, risk sizing, peak/halt хадгалалт, дансны state андуурахгүй байх, invalid data, long/short зардал, gap, нэг лаанд SL/TP, дараагийн open, spread-ийн ирээдүйн мэдээлэл, CLI split/тайлан. Тусдаа кодын review ноцтой асуудал олоогүй; warmup-ийг тайлангийн жинхэнэ үнэлгээний хугацаанаас тусгаарлах жижиг засварыг хийсэн. Native compile болон код/өгөгдлийн hash-уудыг [verification record](../artifacts/baseline-2026-11-05/verification.json)-д хадгалсан.

## Ажиллуулах

Судалгааны цөм Python standard library ашиглана:

```powershell
python -m unittest discover -s tests -v
python -m forexbot data/xmglobal-eurusd-m15-2026-11-05/bars.csv --config data/xmglobal-eurusd-m15-2026-11-05/config.json --output artifacts/new-baseline-run --label fixed-baseline
```

Output хавтас өмнө нь байвал дарж бичихгүй. Түүх шинээр авахад Windows CPython 3.12-ийн `.venv` болон [түгжсэн data dependencies](../requirements-data.txt) ашигласан:

```powershell
.\.venv\Scripts\python.exe -m tools.export_mt5 --terminal "C:\Program Files\MetaTrader 5\terminal64.exe" --credentials-file "C:\Users\Acer\.ssh\oracle-forex-mt5-demo.ini" --start 2024-01-01 --end 2026-11-01 --output data/new-export
```

Нууц үгтэй INI-г чат, source control, artifact-д хуулж болохгүй. Export нь үнийн API ашигладаг; терминал дахь хэрэглэгчийн бусад EA-ийн үйлдлийг удирдахгүй.

## Хязгаар ба дараагийн шат

OHLC симуляц long үед O-L-H-C, short үед O-H-L-C замаар тооцно. Нэг лаанд stop ба target хүрвэл adverse path-аар stop түрүүлнэ. Gap үед хуучин stop үнээр төгс гүйцэтгэл өгөхгүй. Гэхдээ бодит tick дараалал, өөрчлөгдөх спред, fill/rejection/latency болон тэмцээний peak sampling-ийг сэргээхгүй. Иймээс загварын drawdown нь бодит 20%-ийн дүрмийг хангах баталгаа биш.

Зардлын эхлэх таамаглал: spread дор хаяж 10 point, entry/exit тус бүр 2 point adverse slippage, round-trip commission $7/lot. Бодит Standard дансны батлагдсан commission гэсэн утга биш. Swap тооцоогүй; overnight судалгаанд нэмж шалгана. Нэг 10% halt-тай урт туршилт нь давтан тэмцээний календарийг дуурайлгаагүй.

Дараагийн хөгжүүлэлт: зөвхөн development хэсэгт стратегийн сул талыг шинжилж, хязгаарлагдмал өөрчлөлтөө урьдчилан тогтоох; tick/spread/swap өгөгдөлтэй шалгах; шинэ forward хугацаанд shadow дохиог цуглуулж Python/MQL parity шалгах. Дараа нь demo-only order executor, restart/duplicate-order хамгаалалт, серверийн ажиллагааг тусдаа хэрэгжүүлнэ. Тэмцээний холболт батлагдвал тухайн шатны данс/цаг/эрсдэлийн config нэмнэ.

Албан техникийн лавлагаа: [CopyRates closed/current bar индекс](https://www.mql5.com/en/docs/series/copyrates), [Python history range ба UTC request](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py), [account mode/equity](https://www.mql5.com/en/docs/constants/environment_state/accountinformation), [MetaEditor CLI compile](https://www.metatrader5.com/en/metaeditor/help/beginning/integration_ide), [terminal global state хугацаа](https://www.mql5.com/en/docs/globals/globalvariableset).
