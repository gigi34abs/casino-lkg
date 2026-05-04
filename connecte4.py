@group.command(name="connecte4", description="🔴 Duel Puissance 4 contre un autre joueur")
    async def connecte4(self, interaction: discord.Interaction, adversaire: discord.Member, mise: int):
        if adversaire.id == interaction.user.id or adversaire.bot:
            return await interaction.response.send_message("❌ Action impossible.", ephemeral=True)

        u1_solde = self.get_user(interaction.user.id)
        err = self.check_mise(mise, 1, 50000, u1_solde)
        if err: return await interaction.response.send_message(err, ephemeral=True)

        u2_solde = self.get_user(adversaire.id)
        if u2_solde < mise:
            return await interaction.response.send_message(f"❌ **{adversaire.display_name}** n'a pas assez d'argent.", ephemeral=True)

        embed = discord.Embed(
            title="🔴 PUISSANCE 4 : DÉFI",
            description=f"{interaction.user.mention} défie {adversaire.mention} !\n💰 Mise : **{self.fmt(mise)} €**",
            color=0x3498DB # Bleu comme ton image
        )

        view = C4Invite(self, interaction.user, adversaire, mise)
        await interaction.response.send_message(content=adversaire.mention, embed=embed, view=view)

class C4Invite(discord.ui.View):
    def __init__(self, cog, p1, p2, mise):
        super().__init__(timeout=60)
        self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise

    @discord.ui.button(label="Accepter", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, i: discord.Interaction, b):
        if i.user.id != self.p2.id: return await i.response.send_message("❌ Ce n'est pas pour toi.", ephemeral=True)
        
        self.cog.update_money(self.p1.id, -self.mise)
        self.cog.update_money(self.p2.id, -self.mise)
        
        game = C4Game(self.cog, self.p1, self.p2, self.mise)
        await i.response.edit_message(content=None, embed=game.make_embed(), view=game)

    @discord.ui.button(label="Décliner", style=discord.ButtonStyle.danger, emoji="✖️")
    async def deny(self, i: discord.Interaction, b):
        if i.user.id != self.p2.id: return
        await i.response.edit_message(content="❌ Défi refusé.", embed=None, view=None)

class C4Game(discord.ui.View):
    def __init__(self, cog, p1, p2, mise):
        super().__init__(timeout=300)
        self.cog, self.p1, self.p2, self.mise = cog, p1, p2, mise
        # Grille : 6 lignes, 7 colonnes
        self.board = [[0 for _ in range(7)] for _ in range(6)]
        self.turn = p1
        self.symbols = {0: "⚪", 1: "🔴", 2: "🟡"}
        self.finished = False

    def make_embed(self):
        grid_text = ""
        for row in self.board:
            grid_text += "".join([self.symbols[cell] for cell in row]) + "\n"
        grid_text += "1️⃣2️⃣3️⃣4️⃣5️⃣6️⃣7️⃣" # Les chiffres sous les colonnes

        embed = discord.Embed(title="🎮 MATCH EN COURS", color=0x3498DB)
        embed.description = (
            f"🔴 {self.p1.mention} vs 🟡 {self.p2.mention}\n\n"
            f"{grid_text}\n\n"
            f"Tour de : **{self.turn.display_name}**"
        )
        return embed

    def check_win(self, p):
        # Horizontal
        for r in range(6):
            for c in range(4):
                if self.board[r][c] == p and self.board[r][c+1] == p and self.board[r][c+2] == p and self.board[r][c+3] == p: return True
        # Vertical
        for r in range(3):
            for c in range(7):
                if self.board[r][c] == p and self.board[r+1][c] == p and self.board[r+2][c] == p and self.board[r+3][c] == p: return True
        # Diagonal /
        for r in range(3, 6):
            for c in range(4):
                if self.board[r][c] == p and self.board[r-1][c+1] == p and self.board[r-2][c+2] == p and self.board[r-3][c+3] == p: return True
        # Diagonal \
        for r in range(3):
            for c in range(4):
                if self.board[r][c] == p and self.board[r+1][c+1] == p and self.board[r+2][c+2] == p and self.board[r+3][c+3] == p: return True
        return False

    async def play(self, i, col):
        if i.user.id != self.turn.id:
            return await i.response.send_message("❌ Ce n'est pas ton tour !", ephemeral=True)

        # Placer le jeton (cherche la ligne vide la plus basse)
        placed = False
        p_val = 1 if i.user == self.p1 else 2
        for r in range(5, -1, -1):
            if self.board[r][col] == 0:
                self.board[r][col] = p_val
                placed = True
                break
        
        if not placed:
            return await i.response.send_message("❌ Cette colonne est pleine !", ephemeral=True)

        # Vérification victoire
        if self.check_win(p_val):
            self.finished = True
            gain = self.mise * 2
            self.cog.update_money(i.user.id, gain)
            emb = self.make_embed()
            emb.title = "🏆 VICTOIRE !"
            emb.description = f"🔥 {i.user.mention} a gagné **{self.cog.fmt(gain)} €** !\n\n" + emb.description.split("\n\n")[1]
            return await i.response.edit_message(embed=emb, view=None)

        # Tour suivant
        self.turn = self.p2 if self.turn == self.p1 else self.p1
        await i.response.edit_message(embed=self.make_embed(), view=self)

    # Boutons de 1 à 7 (Bleus comme sur l'image)
    @discord.ui.button(label="1", style=discord.ButtonStyle.blurple)
    async def c1(self, i, b): await self.play(i, 0)
    @discord.ui.button(label="2", style=discord.ButtonStyle.blurple)
    async def c2(self, i, b): await self.play(i, 1)
    @discord.ui.button(label="3", style=discord.ButtonStyle.blurple)
    async def c3(self, i, b): await self.play(i, 2)
    @discord.ui.button(label="4", style=discord.ButtonStyle.blurple)
    async def c4(self, i, b): await self.play(i, 3)
    @discord.ui.button(label="5", style=discord.ButtonStyle.blurple)
    async def c5(self, i, b): await self.play(i, 4)
    @discord.ui.button(label="6", style=discord.ButtonStyle.blurple)
    async def c6(self, i, b): await self.play(i, 5)
    @discord.ui.button(label="7", style=discord.ButtonStyle.blurple)
    async def c7(self, i, b): await self.play(i, 6)
