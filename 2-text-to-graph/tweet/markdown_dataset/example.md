# Nodes
### Node ID: Unggahan
**Label**: Unggahan
**Type**: Entity
--

### Node ID: Aku
**Label**: Aku
**Type**: Entity
--

### Node ID: Racial_Bullyingtindakan_Rasisme
**Label**: Racial Bullying/tindakan rasisme
**Type**: Entity
--

### Node ID: Us
**Label**: US
**Type**: Entity
--

### Node ID: Orang_Indonesia
**Label**: Orang Indonesia
**Type**: Entity
--

### Node ID: Orang_Bali
**Label**: Orang Bali
**Type**: Entity
--

### Node ID: Topik
**Label**: Aku mengalami racial bullying oleh sesama orang Indonesia, secara spesifik orang Bali
**Type**: Topic
--

### Node ID: Negatif
**Label**: Negatif
**Type**: Sentiment
--

### Node ID: Penulis_Tidak_Menyangka_Akan_Mendapatkan_Perilaku_Rasisme_Oleh_Sesama_Orang_Indonesia
**Label**: penulis tidak menyangka akan mendapatkan perilaku rasisme oleh sesama orang indonesia
**Type**: Sentiment
--

### Node ID: Racial_Bullying
**Label**: racial bullying
**Type**: Entity
--


# Edges
**Source**: Unggahan
**Target**: Aku
**Label**: mengenai
--

**Source**: Unggahan
**Target**: Topik
**Label**: memilikiTopik
--

**Source**: Unggahan
**Target**: Negatif
**Label**: memilikiSentimen
--

**Source**: Negatif
**Target**: Penulis_Tidak_Menyangka_Akan_Mendapatkan_Perilaku_Rasisme_Oleh_Sesama_Orang_Indonesia
**Label**: memiliki alasan
--

**Source**: Aku
**Target**: Racial_Bullying
**Label**: mendapatkan
--

**Source**: Racial_Bullying
**Target**: Us
**Label**: terjadi di
--

**Source**: Racial_Bullying
**Target**: Orang_Indonesia
**Label**: dilakukan oleh
--

**Source**: Racial_Bullying
**Target**: Orang_Bali
**Label**: dilakukan oleh
--

**Source**: Aku
**Target**: Orang_Bali
**Label**: tidak menjelekkan
--

