# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a
measurement. The authority above everything else is TI's SN76489AN data sheet,
read twice. Below it sit SMS Power's notes and MAME, which are leads rather than
authorities, and an SG-1000 library, which says what software writes but not
what the chip does with it.

Every entry is also in [`conformance/hardware.json`](conformance/hardware.json)
under `notStated`, or in [`conformance/divergences.json`](conformance/divergences.json),
so a program can read what a person reads here.

## What would settle almost all of them

A recording of a discrete SN76489AN's audio output at a rate that resolves a
single input clock, with the chip enable and write strobes captured beside it,
while a test program writes each register in each form. One capture settles the
shift register, its phase, the zero period, the tone 3 edge and what an early
write does. Powering the part repeatedly before any write settles its power-on
state.

## What the data sheet does not print

### The width and taps of the noise shift register

**This package does.** 15 bits, white noise feeding bits 0 and 1 exclusive-or into bit 14, cleared to bit 14 alone, output from bit 0.

**Why it is open.** The data sheet says only that the noise source is a shift register with exclusive-or feedback that cannot lock at zero.

**Where the value came from.** SMS Power's SN76489 notes, from data Charles MacDonald took on an SC-3000H, which carries a discrete SN76489AN. MAME builds the same sequence; the two count as one lineage.

**What would settle it.** A recording of the output in white and periodic noise after a noise write.

### When the shift register's bits reach the output after a noise write

**This package does.** At once: the first shift already shows the cleared register's bit 0.

**Why it is open.** The data sheet says nothing about the output's phase.

**Where the value came from.** This package's reading of SMS Power. MAME puts two delay stages in front of the output, so two zeros come out first; see divergences.json.

**What would settle it.** The same recording, aligned to the write strobe.

### What a period of 0 does

**This package does.** Lets the 10-stage counter run through 1,024 decrements before it borrows.

**Why it is open.** The data sheet does not say.

**Where the value came from.** The data sheet's own counter, followed literally. MAME agrees for TI parts.

**What would settle it.** The output period of a discrete SN76489AN with 0 written to a tone register.

### Which edge of tone 3 clocks the noise in the fourth rate

**This package does.** One shift on each rising toggle of tone 3's flip-flop.

**Why it is open.** Table 3 says only that the fourth rate is tone generator 3's output.

**Where the value came from.** MAME shifts at twice tone 3's period, which fixes the rate and not the edge; the edge is this package's choice.

**What would settle it.** Noise and tone 3 recorded together, with tone 3 attenuated to off, and the shifts aligned to tone 3's edges.

### What the part holds at power on

**This package does.** Scrambles every register, counter, flip-flop, the shift register and the latched address from a seed.

**Why it is open.** The data sheet describes no reset and the part has no reset pin.

**Where the value came from.** SMS Power says discrete chips seem to start with random values. MAME clears them, noting that this needs testing on other chips.

**What would settle it.** Power a discrete SN76489AN repeatedly with no write and record its output.

### What a write made before READY rises does

**This package does.** Applies it at once and starts READY's count again.

**Why it is open.** The data sheet tells the processor to wait for READY and does not say what happens when it does not.

**Where the value came from.** MAME, which applies every write at once.

**What would settle it.** Two writes inside 32 input clocks on a discrete SN76489AN, and which one took effect.

### What a second byte does to an attenuation or noise register

**This package does.** Sets that register's four bits; to the noise register it also clears the shift register.

**Why it is open.** The data sheet describes the second byte for frequency registers only.

**Where the value came from.** MAME.

**What would settle it.** A second byte written after addressing each attenuation register and the noise register.

## Where the data sheet contradicts itself

### Which noise bits select N/1024

**The data sheet says.** Table 3 prints NF0, NF1 as 0 0 for both N/512 and N/1024.

**This package does.** Reads the second row as 0 1, so the two bits count through N/512, N/1024, N/2048 and tone 3, which agrees with the 2/4/8 selector page 8 draws.

**What would settle it.** Another printing of the data sheet.

### Which bits of each byte carry F0 to F9 and A0 to A3

**The data sheet says.** Page 2 makes F0 the most significant bit and Table 1 weighs A0 at 16 dB, with D0 the most significant data line. The data formats on page 4, retyped by a later hand, label the bits the other way round.

**This package does.** Follows the prose and Table 1.

**What would settle it.** An unedited scan of page 4.

### What pin 6 is called

**The data sheet says.** OE on the page 1 pinout, CE everywhere else.

**This package does.** Treats it as CE, folded with WE into `write()`.

**What would settle it.** Another printing of page 1.
